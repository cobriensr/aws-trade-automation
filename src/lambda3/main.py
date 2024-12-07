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
import psutil
from coinbase.rest import RESTClient

MIN_ORDER = {
    "BTCUSD": 0.01,
    "ETHUSD": 0.01,
    "XRPUSD": 0.01,
    "HBARUSD": 1,
    "SOLUSD": 0.01,
    "DOGEUSD": 1,
}

# AVG_ORDER_SIZE = {
#     "BTCUSD": "$993.00",
#     "ETHUSD": "$39.94",
#     "XRPUSD": "$.243",
#     "HBARUSD": "$.344",
#     "SOLUSD": "$2.3533",
#     "DOGEUSD": "$.433",
# }

# Initialize AWS clients
cloudwatch = boto3.client('cloudwatch')

class CoinbaseError(Exception):
    """Custom exception for Coinbase-specific errors"""

# Generate a unique order ID
def generate_order_id():
    return str(uuid.uuid4())

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


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

def publish_metric(name: str, value: float = 1, unit: str = 'Count') -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace='Trading/Coinbase',
            MetricData=[{
                'MetricName': name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now(timezone.utc)
            }]
        )
    except Exception as e:
        logger.error(f"Failed to publish metric {name}: {str(e)}")

def get_api_key() -> Tuple[str, str]:
    """Get Coinbase API credentials with enhanced error handling"""
    try:
        ssm = boto3.client("ssm")
        response = ssm.get_parameters(
            Names=[
                "/tradovate/COINBASE_API_KEY_NAME",
                "/tradovate/COINBASE_PRIVATE_KEY"
            ],
            WithDecryption=True
        )
        
        if len(response['Parameters']) != 2:
            missing = response.get('InvalidParameters', [])
            raise CoinbaseError(f"Missing parameters: {', '.join(missing)}")
            
        param_dict = {p['Name']: p['Value'] for p in response['Parameters']}
        publish_metric('api_key_retrieval_success')
        
        return (
            param_dict["/tradovate/COINBASE_API_KEY_NAME"],
            param_dict["/tradovate/COINBASE_PRIVATE_KEY"]
        )
        
    except ClientError as e:
        publish_metric('api_key_retrieval_error')
        logger.error(f"AWS SSM error: {str(e)}")
        raise CoinbaseError("Failed to retrieve API credentials from all sources") from e

def place_order(client: RESTClient, order_type: str, symbol: str, size: float) -> Dict:
    """Generic order placement function with enhanced error handling"""
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
                base_size=str(size)
            )
        else:  # SELL
            order = client.market_order_sell(
                client_order_id=order_id,
                product_id=formatted_symbol,
                base_size=str(size)
            )
        
        # Record order timing
        duration = (time.time() - start_time) * 1000
        publish_metric(f'{order_type.lower()}_order_duration', duration, 'Milliseconds')
        
        # Process response
        if hasattr(order, 'success_response'):
            order_id = order.success_response.order_id
            try:
                fills = client.get_fills(order_id=order_id)
                fill_details = fills.to_dict()
                publish_metric(f'{order_type.lower()}_order_success')
                return {
                    "success": True,
                    "order_id": order_id,
                    "fills": fill_details
                }
            except Exception as e:
                logger.error(f"Fill retrieval failed for order {order_id}: {str(e)}")
                publish_metric('fill_retrieval_error')
                return {
                    "success": True,
                    "order_id": order_id,
                    "error": "Fill retrieval failed",
                    "details": str(e)
                }
        
        elif hasattr(order, 'error_response'):
            error_msg = order.error_response
            logger.error(f"{order_type} order failed: {error_msg}")
            publish_metric(f'{order_type.lower()}_order_error')
            return {
                "success": False,
                "error": f"{order_type} order failed",
                "details": error_msg
            }
            
    except Exception as e:
        logger.error(f"Order placement error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        publish_metric(f'{order_type.lower()}_order_error')
        return {
            "success": False,
            "error": "Order placement failed",
            "details": str(e)
        }

def list_accounts(api_key: str, api_secret: str) -> str:
    """List Coinbase accounts with error handling"""
    try:
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        accounts = client.get_accounts(
            limit=1,
        )
        return accounts['accounts'][0].to_dict()
    except Exception as e:
        logger.error(f"Failed to list accounts: {str(e)}")
        raise CoinbaseError("Failed to list accounts") from e

def place_buy_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """Place buy order with validation and metrics"""
    try:
        if symbol not in MIN_ORDER:
            publish_metric('invalid_symbol_error')
            raise CoinbaseError(f"Invalid symbol: {symbol}")
            
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        size = MIN_ORDER[symbol]
        
        return place_order(client, "BUY", symbol, size)
        
    except Exception as e:
        publish_metric('buy_order_error')
        logger.error(f"Buy order error: {str(e)}")
        raise

def place_sell_order(api_key: str, api_secret: str, symbol: str) -> Dict:
    """Place sell order with validation and metrics"""
    try:
        if symbol not in MIN_ORDER:
            publish_metric('invalid_symbol_error')
            raise CoinbaseError(f"Invalid symbol: {symbol}")
            
        client = RESTClient(api_key=api_key, api_secret=api_secret)
        size = MIN_ORDER[symbol]
        
        return place_order(client, "SELL", symbol, size)
        
    except Exception as e:
        publish_metric('sell_order_error')
        logger.error(f"Sell order error: {str(e)}")
        raise

def close_position(api_key: str, api_secret: str, symbol: str) -> Dict:
    """
    Close an open position.

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
        logger.debug("REST client initialized successfully")

        # Format symbol
        formatted_symbol = f"{symbol[:3]}-{symbol[3:]}"
        logger.info(f"Order parameters - Formatted Symbol: {formatted_symbol}")

        # Close position
        try:
            order = client.close_position(
                client_order_id=generate_order_id(),
                product_id=formatted_symbol,
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
        logger.error(f"Unexpected error in place_sell_order: {str(e)}", exc_info=True)
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
        logger.debug("REST client initialized successfully")

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
    api_key: str,
    api_secret: str,
    symbol: str,
    direction: str
) -> Dict:
    """Handle position changes with full error handling and metrics"""
    start_time = time.time()
    
    try:
        # Check existing positions
        current_positions = list_orders(api_key, api_secret, symbol)
        if not current_positions["success"]:
            publish_metric('position_check_error')
            raise CoinbaseError(f"Failed to check positions: {current_positions['error']}")
            
        # Close existing positions if any
        if current_positions.get("orders"):
            logger.info(f"Closing existing positions for {symbol}")
            close_result = close_position(api_key, api_secret, symbol)
            if not close_result["success"]:
                publish_metric('position_close_error')
                raise CoinbaseError(f"Failed to close positions: {close_result['error']}")
                
            publish_metric('position_closed')
            logger.info("Existing positions closed successfully")
            
        # Place new order
        if direction == "LONG":
            result = place_buy_order(api_key, api_secret, symbol)
        elif direction == "SHORT":
            result = place_sell_order(api_key, api_secret, symbol)
        else:
            publish_metric('invalid_direction_error')
            raise CoinbaseError(f"Invalid direction: {direction}")
            
        # Record execution time
        duration = (time.time() - start_time) * 1000
        publish_metric('position_change_duration', duration, 'Milliseconds')
        
        if result["success"]:
            publish_metric('position_change_success')
            logger.info(f"Successfully changed position for {symbol} to {direction}")
        else:
            publish_metric('position_change_error')
            logger.error(f"Failed to change position: {result['error']}")
            
        return result
        
    except Exception as e:
        publish_metric('position_change_error')
        logger.error(f"Position change error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        raise CoinbaseError(f"Failed to change position: {str(e)}") from e

def lambda_handler(event, context) -> Dict:
    """Enhanced Lambda handler with comprehensive error handling and metrics"""
    request_id = context.aws_request_id
    start_time = time.time()

    try:
        configure_logger(context)
        logger.info(f"Processing request {request_id}")
        
        # Extract path and handle different endpoints
        path = event.get("rawPath", event.get("path", ""))
        logger.info(f"Request path: {path}")
        
        # Get credentials
        try:
            api_key, api_secret = get_api_key()
        except Exception as e:
            publish_metric('credentials_error')
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Failed to retrieve credentials",
                    "details": str(e),
                    "request_id": request_id
                })
            }
        
        if path.endswith("/coinbasestatus"):
            account_info = list_accounts(api_key, api_secret)
            response = {"statusCode": 200, "body": json.dumps(account_info)}
            return response
        
        # Validate webhook data
        try:
            webhook_data = json.loads(event["body"])
            symbol = webhook_data["market_data"]["symbol"]
            direction = webhook_data["signal"]["direction"]
        except (json.JSONDecodeError, KeyError) as e:
            publish_metric('invalid_webhook_error')
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "Invalid webhook data",
                    "details": str(e),
                    "request_id": request_id
                })
            }
            
        # Process trading signal
        try:
            result = handle_position_change(api_key, api_secret, symbol, direction)
            status_code = 200 if result["success"] else 500
            
            return {
                "statusCode": status_code,
                "body": json.dumps({
                    "success": result["success"],
                    "message": f"Processed {direction} signal for {symbol}",
                    "details": result,
                    "request_id": request_id
                })
            }
            
        except CoinbaseError as e:
            publish_metric('trading_error')
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": str(e),
                    "request_id": request_id
                })
            }
            
    except Exception as e:
        publish_metric('lambda_error')
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "details": str(e),
                "request_id": request_id
            })
        }
        
    finally:
        # Record execution metrics
        duration = (time.time() - start_time) * 1000
        publish_metric('lambda_duration', duration, 'Milliseconds')
        
        # Log request completion
        log_message = f"Request {request_id} completed in {duration:.2f}ms"
        if duration > 5000:
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)
            
        # Monitor memory usage
        try:
            memory_used = psutil.Process().memory_info().rss / 1024 / 1024  # Convert to MB
            publish_metric('memory_used', memory_used, 'Megabytes')
            memory_limit = float(context.memory_limit_in_mb)  # Convert to float
            threshold = int(memory_limit * 0.9)  # Convert the threshold to integer
            if memory_used > threshold:
                logger.warning(f"High memory usage: {memory_used:.2f}MB")
        except ImportError:
            logger.warning("psutil not available - memory monitoring disabled")
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {str(e)}")