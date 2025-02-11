"""Secondary Lambda function for symbol lookup."""

import json
import uuid
import time
import traceback
from datetime import datetime, timezone
import logging
from typing import Dict, Tuple
import boto3
from botocore.exceptions import ClientError
from coinbase.rest import RESTClient

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")


class CoinbaseError(Exception):
    """Custom exception for Coinbase-specific errors"""


class InsufficientBalanceError(Exception):
    """Raised when account balance is insufficient for minimum order size"""


# Generate a unique order ID
def generate_order_id():
    return str(uuid.uuid4())


# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

rest_client = "REST client initialized successfully"


def monitor_concurrent_executions():
    """Monitor concurrent executions and publish metrics"""
    try:
        metrics = [
            {
                "MetricName": "ConcurrentExecutions",
                "Value": 1,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc),
            }
        ]

        cloudwatch.put_metric_data(Namespace="Trading/Coinbase", MetricData=metrics)
    except Exception as e:
        logger.error(f"Error publishing concurrency metrics: {str(e)}")


def configure_logger(context) -> None:
    """Configure logger with Lambda context information"""
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s.%(msecs)03d "
        f"RequestId: {context.aws_request_id} "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.handlers.clear()
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")


def publish_metric(name: str, value: float = 1, unit: str = "Count") -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace="Trading/Coinbase",
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": datetime.now(timezone.utc),
                }
            ],
        )
    except Exception as e:
        logger.error(f"Failed to publish metric {name}: {str(e)}")


def track_error_rate(has_error: bool):
    """Track error rate for the function"""
    try:
        cloudwatch.put_metric_data(
            Namespace="Trading/SymbolLookup",
            MetricData=[
                {
                    "MetricName": "ErrorRate",
                    "Value": 1 if has_error else 0,
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                }
            ],
        )
    except Exception as e:
        logger.error(f"Error publishing error rate metric: {str(e)}")


def get_api_key() -> Tuple[str, str]:
    """Get Coinbase API credentials with enhanced error handling"""
    try:
        ssm = boto3.client("ssm")
        response = ssm.get_parameters(
            Names=[
                "/tradovate/COINBASE_API_KEY_NAME",
                "/tradovate/COINBASE_PRIVATE_KEY",
            ],
            WithDecryption=True,
        )

        if len(response["Parameters"]) != 2:
            missing = response.get("InvalidParameters", [])
            raise CoinbaseError(f"Missing parameters: {', '.join(missing)}")

        param_dict = {p["Name"]: p["Value"] for p in response["Parameters"]}
        publish_metric("api_key_retrieval_success")

        return (
            param_dict["/tradovate/COINBASE_API_KEY_NAME"],
            param_dict["/tradovate/COINBASE_PRIVATE_KEY"],
        )

    except ClientError as e:
        publish_metric("api_key_retrieval_error")
        logger.error(f"AWS SSM error: {str(e)}")
        raise CoinbaseError(
            "Failed to retrieve API credentials from all sources"
        ) from e


def get_account_balance(client: RESTClient, currency: str) -> Tuple[float, str]:
    """
    Get available balance for specific currency

    Args:
        client: RESTClient instance
        currency: Currency code (e.g., 'BTC', 'USD')

    Returns:
        Tuple[float, str]: (balance amount, currency)

    Raises:
        ValueError: If currency not found or currency mismatch
    """
    accounts = client.get_accounts()

    for account in accounts["accounts"]:
        if account["currency"] == currency:
            balance = float(account["available_balance"]["value"])
            returned_currency = account["available_balance"]["currency"]

            # Validate currency matches what we expect
            if returned_currency != currency:
                raise ValueError(
                    f"Currency mismatch: requested {currency}, "
                    f"but got {returned_currency}"
                )

            logger.info(f"Found {currency} balance: {balance}")
            return balance, currency

    raise ValueError(f"No account found for currency: {currency}")


def determine_order_size(
    api_key: str, api_secret: str, symbol: str, direction: str
) -> float:
    """
    Determine the order size based on symbol and direction, checking appropriate asset balance

    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')
        direction (str): "LONG" or "SHORT"

    Returns:
        float: Order size in base currency

    Raises:
        ValueError: If currency validation fails or calculation error
        InsufficientBalanceError: If balance too low for minimum order
    """
    client = RESTClient(api_key=api_key, api_secret=api_secret)
    logger.debug(rest_client)

    # Parse the symbol to get base and quote currencies
    base_currency = symbol[:3]  # e.g., 'BTC' from 'BTCUSD'
    quote_currency = symbol[3:]  # e.g., 'USD' from 'BTCUSD'

    MIN_SIZES = {
        "BTC": 0.000001,  # Minimum BTC order size
        "ETH": 0.001,  # Minimum ETH order size
        "XRP": 1,  # Minimum XRP order size
    }

    if base_currency not in MIN_SIZES:
        raise ValueError(f"Minimum order size not defined for {base_currency}")

    MIN_ORDER_SIZE = MIN_SIZES[base_currency]

    try:
        # Get prices first as we'll need them for both directions
        formatted_symbol = f"{base_currency}-{quote_currency}"
        bid_ask_response = client.get_best_bid_ask(product_ids=[formatted_symbol])
        pricebook = bid_ask_response["pricebooks"][0]

        best_bid = float(pricebook["bids"][0]["price"]) if pricebook["bids"] else None
        best_ask = float(pricebook["asks"][0]["price"]) if pricebook["asks"] else None

        if best_bid is None or best_ask is None:
            raise ValueError("Unable to get valid bid/ask prices")

        # Check appropriate balance based on direction
        if direction == "LONG":
            # For longs, we need quote currency (e.g., USD)
            available_balance, returned_currency = get_account_balance(
                client, quote_currency
            )
            if returned_currency != quote_currency:
                raise ValueError(
                    f"Currency mismatch for LONG order: Expected {quote_currency}, "
                    f"got {returned_currency}"
                )

            max_risk = available_balance * 0.02
            order_size = round(max_risk / best_ask, 8)
            logger.debug(
                "Long order size calculated with 2%% risk of %s: %s %s",
                quote_currency,
                order_size,
                base_currency,
            )

        elif direction == "SHORT":
            # For shorts, we need base currency (e.g., BTC) as we're selling it
            available_balance, returned_currency = get_account_balance(
                client, base_currency
            )
            if returned_currency != base_currency:
                raise ValueError(
                    f"Currency mismatch for SHORT order: Expected {base_currency}, "
                    f"got {returned_currency}"
                )

            BUFFER_FACTOR = 0.995  # Keep 0.5% as buffer for fees
            order_size = round(available_balance * BUFFER_FACTOR, 8)
            logger.debug(
                "Short order size using full %s balance with buffer: %s",
                base_currency,
                order_size,
            )

        else:
            raise ValueError(f"Invalid direction: {direction}")

        # Check minimum order size
        if order_size < MIN_ORDER_SIZE:
            raise InsufficientBalanceError(
                f"Calculated order size ({order_size} {base_currency}) "
                f"below minimum ({MIN_ORDER_SIZE} {base_currency})"
            )

        # Additional validation for shorts
        if direction == "SHORT" and order_size > available_balance:
            raise InsufficientBalanceError(
                f"Calculated short size ({order_size} {base_currency}) "
                f"exceeds available balance ({available_balance} {base_currency})"
            )

        # Log full order details
        logger.info(
            "Order size calculated for %s %s: %s %s (Price: %s %s)",
            direction,
            symbol,
            order_size,
            base_currency,
            best_ask if direction == "LONG" else best_bid,
            quote_currency,
        )

        return order_size

    except Exception as e:
        logger.error(f"Error calculating order size: {str(e)}")
        raise ValueError(f"Failed to calculate order size: {str(e)}") from e


def place_order(
    api_key: str, api_secret: str, order_type: str, symbol: str, size: float
) -> Dict:
    """
    Generic order placement function with enhanced error handling

    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        order_type (str): Order type ('BUY' or 'SELL')
        symbol (str): Trading symbol (e.g., 'BTCUSD')
        size (float): Order size

    Returns:
        Dict: Order status and details
    """

    # Initialize REST client
    client = RESTClient(api_key=api_key, api_secret=api_secret)
    logger.debug(rest_client)

    start_time = time.time()
    order_id = str(uuid.uuid4())

    try:
        logger.info(f"Placing {order_type} order for {symbol} - Size: {size}")
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"

        # Place order based on type
        if order_type == "BUY":
            order = client.market_order_buy(
                client_order_id=order_id,
                product_id=formatted_symbol,
                base_size=str(size),
            )
        else:  # SELL
            order = client.market_order_sell(
                client_order_id=order_id,
                product_id=formatted_symbol,
                base_size=str(size),
            )

        # Record order timing
        duration = (time.time() - start_time) * 1000
        publish_metric(f"{order_type.lower()}_order_duration", duration, "Milliseconds")

        # Process response - Updated to handle new response structure
        if hasattr(order, "success_response"):
            success_data = order.success_response
            order_id = getattr(success_data, "order_id", None)
            if order_id:
                try:
                    fills = client.get_fills(order_id=order_id)
                    fill_details = (
                        fills.to_dict() if hasattr(fills, "to_dict") else fills
                    )
                    publish_metric(f"{order_type.lower()}_order_success")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "fills": fill_details,
                    }
                except Exception as e:
                    logger.error(
                        f"Fill retrieval failed for order {order_id}: {str(e)}"
                    )
                    publish_metric("fill_retrieval_error")
                    return {
                        "success": True,
                        "order_id": order_id,
                        "error": "Fill retrieval failed",
                        "details": str(e),
                    }
            else:
                # Handle successful order but missing order_id
                logger.warning("Order successful but no order_id in response")
                return {
                    "success": True,
                    "order_id": order_id,  # Using client-generated ID
                    "details": "Order placed successfully but ID not returned",
                }

        # Handle error response
        error_msg = None
        if hasattr(order, "error_response"):
            error_msg = str(order.error_response)
        elif hasattr(order, "failure_reason"):
            error_msg = str(order.failure_reason)
        else:
            error_msg = "Unknown error in order response"

        logger.error(f"{order_type} order failed: {error_msg}")
        publish_metric(f"{order_type.lower()}_order_error")
        return {
            "success": False,
            "error": f"{order_type} order failed",
            "details": error_msg,
        }

    except Exception as e:
        logger.error(f"Order placement error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        publish_metric(f"{order_type.lower()}_order_error")
        return {"success": False, "error": "Order placement failed", "details": str(e)}


def list_accounts(api_key: str, api_secret: str) -> str:
    """List Coinbase accounts with error handling"""
    try:
        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug(rest_client)

        accounts = client.get_accounts(
            limit=1,
        )
        return accounts["accounts"][0].to_dict()
    except Exception as e:
        logger.error(f"Failed to list accounts: {str(e)}")
        raise CoinbaseError("Failed to list accounts") from e


def place_buy_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """Place buy order with validation and metrics"""
    try:
        # Calculate order size for LONG position
        order_size = determine_order_size(api_key, api_secret, symbol, "LONG")
        return place_order(api_key, api_secret, "BUY", symbol, order_size)

    except Exception as e:
        publish_metric("buy_order_error")
        logger.error(f"Buy order error: {str(e)}")
        raise


def place_sell_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """Place sell order with validation and metrics"""
    try:
        # Calculate order size for SHORT position
        order_size = determine_order_size(api_key, api_secret, symbol, "SHORT")
        return place_order(api_key, api_secret, "SELL", symbol, order_size)

    except Exception as e:
        publish_metric("sell_order_error")
        logger.error(f"Sell order error: {str(e)}")
        raise


def close_position(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    Close an open position by placing an opposite order.

    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')

    Returns:
        Dict: Response containing order status and details

    Raises:
        Exception: If any critical error occurs during order placement
    """
    try:
        logger.info(f"Closing position for symbol: {symbol}")

        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug(rest_client)

        # Format symbol
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Order parameters - Formatted Symbol: {formatted_symbol}")

        # Get current positions
        try:
            orders = client.list_orders(
                product_ids=[formatted_symbol],
                product_type="SPOT",
                order_types=["MARKET"],
                limit=1,
                sort_by="LAST_FILL_TIME",
            )

            if not orders.orders:
                logger.info("No open positions found to close")
                return {"success": True, "message": "No positions to close"}

            last_order = orders.orders[0]
            is_long = last_order.side == "BUY"
            position_size = str(abs(float(last_order.base_size)))

            # Place opposite order to close position
            if is_long:
                order = client.market_order_sell(
                    client_order_id=generate_order_id(),
                    product_id=formatted_symbol,
                    base_size=position_size,
                )
            else:
                order = client.market_order_buy(
                    client_order_id=generate_order_id(),
                    product_id=formatted_symbol,
                    base_size=position_size,
                )

            logger.info(f"Order placement response received: {json.dumps(order)}")

        except Exception as e:
            logger.error(f"Failed to place market order: {str(e)}")
            return {
                "success": False,
                "error": "Order placement failed",
                "details": str(e),
            }

        # Process order response
        if hasattr(order, "success_response"):
            try:
                order_id = order.success_response.order_id
                fills = client.get_fills(order_id=order_id)
                fill_details = fills.to_dict()

                logger.info(f"Order successful - Order ID: {order_id}")
                logger.debug(f"Fill details: {json.dumps(fill_details, indent=2)}")

                return {"success": True, "order_id": order_id, "fills": fill_details}
            except Exception as e:
                logger.error(f"Failed to process fills for order {order_id}: {str(e)}")
                return {
                    "success": True,
                    "order_id": order_id,
                    "error": "Fill retrieval failed",
                    "details": str(e),
                }
        elif hasattr(order, "error_response"):
            error_msg = order.error_response
            logger.error(f"Order placement failed: {error_msg}")
            return {"success": False, "error": "Order failed", "details": error_msg}

    except Exception as e:
        logger.error(f"Unexpected error in close_position: {str(e)}", exc_info=True)
        return {"success": False, "error": "Critical error", "details": str(e)}


def list_orders(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    List open orders for a given symbol.

    Args:
        api_key (str): Coinbase API key
        api_secret (str): Coinbase API secret
        symbol (str): Trading symbol (e.g., 'BTCUSD')

    Returns:
        Dict: Response containing orders and status details
    """
    try:
        logger.info(f"Retrieving orders for symbol: {symbol}")

        # Initialize REST client
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        logger.debug(rest_client)

        # Format symbol
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Formatted Symbol: {formatted_symbol}")

        try:
            orders = client.list_orders(
                product_ids=[formatted_symbol],
                product_type="SPOT",
                order_types=["MARKET"],
                limit=1,
                sort_by="LAST_FILL_TIME",
            )
            logger.info(f"Orders retrieved successfully for {formatted_symbol}")

            # Convert orders to dictionary for return
            orders_dict = orders.to_dict()
            logger.debug(f"Orders details: {json.dumps(orders_dict, indent=2)}")

            return {"success": True, "orders": orders_dict}

        except Exception as e:
            logger.error(f"Failed to retrieve orders: {str(e)}")
            return {
                "success": False,
                "error": "Order retrieval failed",
                "details": str(e),
            }

    except Exception as e:
        logger.error(f"Unexpected error in list_orders: {str(e)}", exc_info=True)
        return {"success": False, "error": "Critical error", "details": str(e)}


def handle_position_change(
    api_key: str, api_secret: str, symbol: str, direction: str
) -> Dict:
    """Handle position changes with asset-specific balance checking"""
    start_time = time.time()

    try:
        # Check existing positions
        current_positions = list_orders(api_key, api_secret, symbol)
        if not current_positions["success"]:
            publish_metric("position_check_error")
            raise CoinbaseError(
                f"Failed to check positions: {current_positions['error']}"
            )

        # Close existing positions if any
        if current_positions.get("orders"):
            logger.info(f"Closing existing positions for {symbol}")
            close_result = close_position(api_key, api_secret, symbol)

            if not close_result["success"]:
                publish_metric("position_close_error")
                raise CoinbaseError(
                    f"Failed to close positions: {close_result['error']}"
                )

            publish_metric("position_closed")
            logger.info("Existing positions closed successfully")

        try:
            # Calculate order size based on direction and symbol
            order_size = determine_order_size(api_key, api_secret, symbol, direction)

            # Place the order
            if direction == "LONG":
                result = place_order(api_key, api_secret, "BUY", symbol, order_size)
            elif direction == "SHORT":
                result = place_order(api_key, api_secret, "SELL", symbol, order_size)
            else:
                publish_metric("invalid_direction_error")
                raise CoinbaseError(f"Invalid direction: {direction}")

        except InsufficientBalanceError as e:
            logger.warning(str(e))
            return {
                "success": False,
                "error": "Insufficient balance",
                "details": str(e),
            }

        # Record execution time
        duration = (time.time() - start_time) * 1000
        publish_metric("position_change_duration", duration, "Milliseconds")

        if result["success"]:
            publish_metric("position_change_success")
            logger.info(f"Successfully changed position for {symbol} to {direction}")
        else:
            publish_metric("position_change_error")
            logger.error(f"Failed to change position: {result['error']}")

        return result

    except Exception as e:
        publish_metric("position_change_error")
        logger.error(f"Position change error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        raise CoinbaseError(f"Failed to change position: {str(e)}") from e


def lambda_handler(event, context) -> Dict:
    """Enhanced Lambda handler with comprehensive error handling and metrics"""
    request_id = context.aws_request_id
    start_time = time.time()
    has_error = False

    try:
        # Track concurrent executions at start
        monitor_concurrent_executions()
        configure_logger(context)
        logger.info(f"Processing request {request_id}")

        # Extract path and handle different endpoints
        path = event.get("rawPath", event.get("path", ""))
        logger.info(f"Request path: {path}")

        # Get credentials
        try:
            api_key, api_secret = get_api_key()
        except Exception as e:
            publish_metric("credentials_error")
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Failed to retrieve credentials",
                        "details": str(e),
                        "request_id": request_id,
                    }
                ),
            }

        if path.endswith("/coinbasestatus"):
            account_info = list_accounts(api_key, api_secret)
            response = {"statusCode": 200, "body": json.dumps(account_info)}
            return response

        # Enhanced webhook data validation
        try:
            # Handle both direct Lambda invocations and API Gateway events
            if isinstance(event, dict):
                if "body" in event:
                    # API Gateway event
                    if isinstance(event["body"], str):
                        webhook_data = json.loads(event["body"])
                    elif isinstance(event["body"], dict):
                        webhook_data = event["body"]
                    else:
                        raise ValueError(f"Unexpected body type: {type(event['body'])}")
                else:
                    # Direct Lambda invocation
                    webhook_data = event
            else:
                raise ValueError("Invalid event format")

            # Validate required fields exist
            if "market_data" not in webhook_data:
                raise KeyError("Missing market_data in webhook")
            if "symbol" not in webhook_data["market_data"]:
                raise KeyError("Missing symbol in market_data")
            if "signal" not in webhook_data:
                raise KeyError("Missing signal in webhook")
            if "direction" not in webhook_data["signal"]:
                raise KeyError("Missing direction in signal")

            # Extract key fields
            symbol = webhook_data["market_data"]["symbol"]
            direction = webhook_data["signal"]["direction"]

            # Log successful parsing
            logger.info(
                f"Successfully parsed webhook data for {symbol} - Direction: {direction}"
            )
            logger.debug(f"Full webhook data: {json.dumps(webhook_data)}")

        except json.JSONDecodeError as e:
            has_error = True
            publish_metric("invalid_webhook_error")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Invalid JSON in webhook data",
                        "details": str(e),
                        "request_id": request_id,
                    }
                ),
            }
        except KeyError as e:
            has_error = True
            publish_metric("invalid_webhook_error")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Missing required fields in webhook data",
                        "details": str(e),
                        "request_id": request_id,
                    }
                ),
            }
        except Exception as e:
            has_error = True
            publish_metric("invalid_webhook_error")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Invalid webhook data",
                        "details": str(e),
                        "request_id": request_id,
                    }
                ),
            }

        # Process trading signal
        try:
            result = handle_position_change(api_key, api_secret, symbol, direction)
            status_code = 200 if result["success"] else 500

            return {
                "statusCode": status_code,
                "body": json.dumps(
                    {
                        "success": result["success"],
                        "message": f"Processed {direction} signal for {symbol}",
                        "details": result,
                        "request_id": request_id,
                    }
                ),
            }

        except CoinbaseError as e:
            has_error = True
            publish_metric("trading_error")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": str(e), "request_id": request_id}),
            }

    except Exception as e:
        has_error = True
        publish_metric("lambda_error")
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Internal server error",
                    "details": str(e),
                    "request_id": request_id,
                }
            ),
        }

    finally:
        # Track error rate
        track_error_rate(has_error)
        # Record execution metrics
        duration = (time.time() - start_time) * 1000
        publish_metric("lambda_duration", duration, "Milliseconds")

        # Log request completion
        log_message = f"Request {request_id} completed in {duration:.2f}ms"
        if duration > 5000:
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)
