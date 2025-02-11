"""Main Lambda function for tradingview webhooks."""

import os
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Tuple, Any, Optional
import boto3
from botocore.exceptions import ClientError
from trading.oanda import (
    check_account_status,
    check_position_exists,
    close_short_position,
    close_long_position,
    create_long_market_order,
    create_short_market_order,
)
from trading.tradovate import (
    get_auth_token,
    get_all_positions,
    get_accounts,
    get_contract_info,
    get_cash_balance_snapshot,
    liquidate_position,
    place_buy_order,
    place_sell_order,
)
from trading.metrics_manager import TradovateMetricsManager

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")
lambda_client = boto3.client("lambda")

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production


class TradingWebhookError(Exception):
    """Custom exception for webhook processing errors"""


class SymbolCache:
    """
    Handles reading symbol mappings from the DynamoDB cache.
    This is a simplified version that only reads from the cache.
    """

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.SYMBOL_CACHE_PREFIX = "symbol_mapping:"

    def get_mapped_symbol(self, continuous_symbol: str) -> Optional[str]:
        """
        Look up the actual contract symbol from the cache.

        Args:
            continuous_symbol (str): The continuous contract symbol (e.g., 'ES1!')

        Returns:
            Optional[str]: The mapped actual contract symbol (e.g., 'ESH5') or None if not found
        """
        try:
            # Construct the cache key
            cache_key = f"{self.SYMBOL_CACHE_PREFIX}{continuous_symbol}"

            # Try to get the item from DynamoDB
            response = self.table.get_item(Key={"cache_key": cache_key})

            # If no item found or expired, return None
            if "Item" not in response:
                logger.info(f"No cache entry found for {continuous_symbol}")
                return None

            item = response["Item"]
            current_time = int(datetime.now(timezone.utc).timestamp())

            # Check if the cached item has expired
            if "ttl" in item and item["ttl"] < current_time:
                logger.info(f"Cache expired for {continuous_symbol}")
                return None

            # Parse and return the cached symbol
            if "cache_data" in item:
                cache_data = json.loads(item["cache_data"])
                return cache_data.get("actual_symbol")

            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None


# Initialize the cache reader with the table name
symbol_cache = SymbolCache(
    os.environ.get("CACHE_TABLE_NAME", "trading-prod-tradovate-cache")
)


def monitor_concurrent_executions(context):
    try:
        metrics = [
            {
                "MetricName": "ConcurrentExecutions",
                "Value": 1,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc),
            },
            {
                "MetricName": "ProvisionedConcurrencyUtilization",
                "Value": 1,
                "Unit": "Count",
                "Timestamp": datetime.now(timezone.utc),
            },
        ]

        cloudwatch.put_metric_data(
            Namespace=f"Trading/Webhook/{context.function_name}", MetricData=metrics
        )
    except Exception as e:
        logger.error(f"Error publishing concurrency metrics: {str(e)}")


def publish_metric(name: str, value: float = 1, unit: str = "Count") -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace="Trading/Webhook",
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


def configure_logger(context) -> None:
    """Configure logger with Lambda context information and structured formatting"""
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s.%(msecs)03d "
        f"RequestId: {context.aws_request_id} "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear existing handlers and add new one
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Log context information
    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")
    logger.info(f"Function Memory: {context.memory_limit_in_mb}MB")
    logger.info(f"Remaining Time: {context.get_remaining_time_in_millis()}ms")


def get_credentials() -> Tuple[str, str, str, str, str, str, str]:
    """Get credentials with enhanced error handling"""
    try:
        ssm = boto3.client("ssm")
        params = [
            "/tradovate/OANDA_SECRET",
            "/tradovate/OANDA_ACCOUNT",
            "/tradovate/USERNAME",
            "/tradovate/PASSWORD",
            "/tradovate/DEVICE_ID",
            "/tradovate/CID",
            "/tradovate/SECRET",
        ]

        # Batch get parameters
        response = ssm.get_parameters(Names=params, WithDecryption=True)

        if len(response["Parameters"]) != len(params):
            missing = response.get("InvalidParameters", [])
            raise ValueError(f"Missing parameters: {', '.join(missing)}")

        param_dict = {p["Name"]: p["Value"] for p in response["Parameters"]}

        return (
            param_dict["/tradovate/OANDA_SECRET"],
            param_dict["/tradovate/OANDA_ACCOUNT"],
            param_dict["/tradovate/USERNAME"],
            param_dict["/tradovate/PASSWORD"],
            param_dict["/tradovate/DEVICE_ID"],
            param_dict["/tradovate/CID"],
            param_dict["/tradovate/SECRET"],
        )

    except ClientError as e:
        logger.error(f"AWS SSM error: {str(e)}")
        raise ValueError("AWS SSM error:") from e


def invoke_lambda_function(function_name: str, payload: Dict[str, Any] = None) -> Dict:
    """Generic Lambda invocation with enhanced error handling and status code propagation"""
    start_time = time.time()
    try:
        logger.info(f"Invoking Lambda function: {function_name}")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload) if payload else "{}",
        )

        duration = (time.time() - start_time) * 1000
        publish_metric(f"{function_name}_duration", duration, "Milliseconds")

        # Check Lambda invocation status
        if response["StatusCode"] != 200:
            logger.error(
                f"Lambda invocation failed with status code: {response['StatusCode']}"
            )
            raise TradingWebhookError(
                f"Lambda invocation failed: {response['StatusCode']}"
            )

        # Parse the payload
        payload_str = response["Payload"].read()
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Lambda response: {str(e)}")
            logger.error(f"Raw payload: {payload_str}")
            raise TradingWebhookError("Invalid response format from Lambda") from e

        # Check for Lambda execution errors
        if "FunctionError" in response:
            error_msg = payload.get("errorMessage", "Unknown error")
            logger.error(f"Lambda execution failed: {error_msg}")
            raise TradingWebhookError(f"Lambda execution failed: {error_msg}")

        # Extract status code and body from payload
        if isinstance(payload, dict):
            status_code = payload.get("statusCode")
            body = payload.get("body")

            # Log the complete response for debugging
            logger.debug(f"Lambda response - Status: {status_code}, Body: {body}")

            # If status code exists, use it for error handling
            if status_code is not None:
                if status_code >= 400:
                    # Parse the error message from the body
                    try:
                        error_details = (
                            json.loads(body) if isinstance(body, str) else body
                        )
                        error_msg = error_details.get("error", "Unknown error")
                        details = error_details.get("details", "")
                        request_id = error_details.get("request_id", "")

                        logger.error(
                            f"Lambda returned error status {status_code}: {error_msg}"
                        )
                        if details:
                            logger.error(f"Error details: {details}")
                        if request_id:
                            logger.error(f"Request ID: {request_id}")

                        # Propagate the error response
                        return {"statusCode": status_code, "body": body}
                    except json.JSONDecodeError as exc:
                        logger.error(f"Failed to parse error body: {body}")
                        raise TradingWebhookError(
                            f"Lambda returned status {status_code}"
                        ) from exc

        logger.info(f"Successfully invoked Lambda function: {function_name}")
        return payload

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]
        logger.error(f"AWS Lambda ClientError: {error_code} - {error_message}")
        publish_metric(f"{function_name}_error")
        raise TradingWebhookError(
            f"Failed to invoke {function_name}: {error_code} - {error_message}"
        ) from e
    except Exception as e:
        logger.error(f"Lambda invocation error: {str(e)}")
        publish_metric(f"{function_name}_error")
        raise TradingWebhookError(f"Failed to invoke {function_name}: {str(e)}") from e


def handle_oanda_trade(
    account: str, symbol: str, signal_direction: str, secret: str
) -> Dict:
    """Handle OANDA trading logic with metrics and error handling"""
    try:
        # Check position existence
        has_position = check_position_exists(
            account_id=account, instrument=symbol, access_token=secret
        )
        logger.info(f"Position check for {symbol}: {has_position}")

        if has_position and signal_direction == "LONG":
            # Close any existing short position first
            close_short_position(
                account_id=account, instrument=symbol, access_token=secret
            )
            # Create new long position and return its result
            order_result = create_long_market_order(
                account_id=account, instrument=symbol, access_token=secret
            )

        elif has_position and signal_direction == "SHORT":
            # Close any existing long position first
            close_long_position(
                account_id=account, instrument=symbol, access_token=secret
            )
            # Create new short position and return its result
            order_result = create_short_market_order(
                account_id=account, instrument=symbol, access_token=secret
            )

        elif not has_position and signal_direction == "LONG":
            # Simply create new long position and return its result
            order_result = create_long_market_order(
                account_id=account, instrument=symbol, access_token=secret
            )

        elif not has_position and signal_direction == "SHORT":
            # Simply create new short position and return its result
            order_result = create_short_market_order(
                account_id=account, instrument=symbol, access_token=secret
            )

        else:
            raise TradingWebhookError(
                f"Invalid position/direction combination: {has_position}/{signal_direction}"
            )

        # Check if any errors occurred in the order result
        if "error" in order_result or "errorText" in order_result:
            error_msg = order_result.get("error") or order_result.get("errorText")
            raise TradingWebhookError(f"Trade action failed: {error_msg}")

        publish_metric("oanda_trade_success")
        return order_result

    except Exception as e:
        publish_metric("oanda_trade_error")
        logger.error(f"OANDA trade error: {str(e)}")
        raise


def handle_futures_trade(
    username: str,
    password: str,
    device_id: str,
    cid: str,
    tradovate_secret: str,
    symbol: str,
    signal_direction: str,
) -> Dict:
    """Handle futures trading logic with enhanced error handling"""
    try:
        # Authenticate
        access_token, expiration_time = get_auth_token(
            username=username,
            password=password,
            device_id=device_id,
            cid=cid,
            secret=tradovate_secret,
        )

        if not access_token:
            raise TradingWebhookError("Failed to obtain Tradovate access token")

        logger.info(f"Authenticated successfully, token expires: {expiration_time}")

        # Replace the Lambda 2 invocation with this:
        try:
            # Look up the symbol in the cache
            mapped_symbol = symbol_cache.get_mapped_symbol(symbol)

            if not mapped_symbol:
                logger.error(f"No cached mapping found for symbol: {symbol}")
                logger.error("Symbol lookup failed - cache miss")
                raise TradingWebhookError(
                    f"No symbol mapping found in cache for: {symbol}. "
                    "Please ensure the symbol mapping service has run recently."
                )
            logger.info(
                f"Successfully found cached mapping: {symbol} -> {mapped_symbol}"
            )
        except ClientError as e:
            logger.error(f"DynamoDB error looking up symbol: {str(e)}")
            raise TradingWebhookError(
                f"Database error during symbol lookup: {str(e)}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during symbol lookup: {str(e)}")
            raise TradingWebhookError(f"Symbol lookup failed: {str(e)}") from e

        # Get default account ID first
        account_id = get_accounts(
            username=username,
            password=password,
            device_id=device_id,
            cid=cid,
            secret=tradovate_secret,
        )

        # Get current positions
        positions = get_all_positions(access_token)

        if positions:
            # There are existing positions - liquidate and then place new order
            logger.info("Found existing positions, liquidating first")
            contracts_ids = [position["contractId"] for position in positions]
            contract_names_with_ids = get_contract_info(
                token=access_token, contract_ids=contracts_ids
            )
            # Log full position details for debugging
            logger.info(f"Found existing positions, total positions: {len(positions)}")
            logger.debug(f"Position details: {positions}")

            # Liquidate all existing positions
            for contract in contract_names_with_ids:
                # Only liquidate if there's an actual position
                if mapped_symbol in contract["contractName"]:
                    try:
                        liquidate_result = liquidate_position(
                            contract_id=contract["contractId"],
                            account_id=account_id,
                            token=access_token,
                        )

                        # Verify successful liquidation based on response
                        if "orderId" in liquidate_result:
                            logger.info(
                                f"Successfully liquidated position with Order ID: {liquidate_result['orderId']}"
                            )
                        else:
                            logger.error(
                                f"Unexpected liquidation response format: {liquidate_result}"
                            )
                            if (
                                "failureReason" in liquidate_result
                                or "failureText" in liquidate_result
                            ):
                                error_msg = liquidate_result.get(
                                    "failureText", liquidate_result.get("failureReason")
                                )
                                raise TradingWebhookError(
                                    f"Liquidation failed: {error_msg}"
                                )
                            raise TradingWebhookError(
                                "Failed to liquidate position - unexpected response format"
                            )

                    except Exception as e:
                        logger.error(f"Error liquidating position: {contract}")
                        raise TradingWebhookError(
                            f"Failed to liquidate position: {str(e)}"
                        ) from e
        else:
            logger.info("No existing positions found")

        # Place new order based on signal direction
        logger.info(
            f"Placing {'BUY' if signal_direction == 'LONG' else 'SELL'} order for {mapped_symbol}"
        )

        if signal_direction == "LONG":
            order_result = place_buy_order(
                username=username,
                instrument=mapped_symbol,
                account_id=account_id,
                quantity=1,
                token=access_token,
            )
        else:  # signal_direction == "SHORT"
            order_result = place_sell_order(
                username=username,
                instrument=mapped_symbol,
                account_id=account_id,
                quantity=1,
                token=access_token,
            )

        logger.info(f"Order placement result: {order_result}")

        if "error" in order_result or "errorText" in order_result:
            error_msg = order_result.get("error") or order_result.get("errorText")
            raise TradingWebhookError(f"Order placement failed: {error_msg}")

        publish_metric("futures_trade_success")
        return {
            "status": "success",
            "order_result": order_result,
            "symbol": mapped_symbol,
            "direction": "BUY" if signal_direction == "LONG" else "SELL",
        }

    except Exception as e:
        publish_metric("futures_trade_error")
        logger.error(f"Futures trade error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        raise TradingWebhookError(f"Futures trade failed: {str(e)}") from e


def lambda_handler(event, context) -> Dict:
    """Main Lambda handler with enhanced metrics tracking and comprehensive error handling"""

    # Initialize metrics manager at the start
    metrics_manager = TradovateMetricsManager()

    # Add operation-specific dimensions
    operation_dimensions = [
        {"Name": "FunctionName", "Value": context.function_name},
        {"Name": "FunctionVersion", "Value": context.function_version},
    ]
    metrics_manager.set_default_dimensions(operation_dimensions)

    request_id = context.aws_request_id

    try:
        # Configure logging
        configure_logger(context)
        logger.info(
            f"Lambda cold start check - Function memory: {context.memory_limit_in_mb}MB"
        )
        logger.info(
            f"Concurrent execution context: {context.function_name}-{context.aws_request_id}"
        )

        # Monitor concurrent executions with enhanced metrics
        metrics_manager.publish_metric_with_zero(
            "ConcurrentExecutions",
            1,
            "Count",
            [{"Name": "ExecutionType", "Value": "Active"}],
        )

        # Validate required environment variables
        required_env_vars = ["LAMBDA2_FUNCTION_NAME"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        logger.info(f"Processing request {request_id}")
        logger.debug(f"Event: {json.dumps(event, indent=2)}")

        # Get credentials
        creds = get_credentials()

        # Extract path and handle different endpoints
        path = event.get("rawPath", event.get("path", ""))
        logger.info(f"Request path: {path}")

        # Set operation name based on endpoint
        if path.endswith("/healthcheck"):
            return {
                "statusCode": 200,
                "body": "ok",
                "headers": {"Content-Type": "application/json"},
            }
        elif path.endswith("/oandastatus"):
            status = check_account_status(account_id=creds[1], access_token=creds[0])
            return {"statusCode": 200, "body": json.dumps(status)}
        elif path.endswith("/tradovatestatus"):
            token, _ = get_auth_token(
                username=creds[2],
                password=creds[3],
                device_id=creds[4],
                cid=creds[5],
                secret=creds[6],
            )
            account_id = get_accounts(
                username=creds[2],
                password=creds[3],
                device_id=creds[4],
                cid=creds[5],
                secret=creds[6],
            )
            balance = get_cash_balance_snapshot(token, account_id)
            return {"statusCode": 200, "body": json.dumps(balance)}
        elif path.endswith("/webhook"):
            webhook_data = json.loads(event["body"])
            signal_direction = webhook_data["signal"]["direction"]
            symbol = webhook_data["market_data"]["symbol"]
            exchange = webhook_data["market_data"]["exchange"]
            timestamp = webhook_data["market_data"].get("timestamp")

            # Enhanced webhook metrics dimensions
            webhook_dimensions = [
                {"Name": "Exchange", "Value": exchange},
                {"Name": "Symbol", "Value": symbol},
                {"Name": "Direction", "Value": signal_direction},
            ]
            metrics_manager.publish_metric_with_zero(
                "webhook_received", 1, "Count", webhook_dimensions
            )

            # Log request details
            logger.info("==================== BEGIN PROCESSING ====================")
            logger.info(f"Processing webhook - Symbol: {symbol}")
            logger.info(f"Exchange: {exchange}")
            logger.info(f"Direction: {signal_direction}")
            logger.info(f"Signal Timestamp: {timestamp}")
            logger.info(f"Lambda Request ID: {context.aws_request_id}")

            # Handle different exchanges
            if exchange == "COINBASE":
                result = invoke_lambda_function("trading-prod-coinbase", webhook_data)
                response = (
                    result
                    if isinstance(result, dict) and "statusCode" in result
                    else {"statusCode": 200, "body": json.dumps(result)}
                )
                return response
            elif exchange == "OANDA":
                result = handle_oanda_trade(
                    creds[1], symbol, signal_direction, creds[0]
                )
                response = {"statusCode": 200, "body": json.dumps(result)}
            elif exchange in [
                "NYMEX",
                "COMEX",
                "CBOT",
                "CBOT_MINI",
                "CME",
                "CME_MINI",
                "ICEUS",
            ]:
                result = handle_futures_trade(
                    creds[2],
                    creds[3],
                    creds[4],
                    creds[5],
                    creds[6],
                    symbol,
                    signal_direction,
                )
                response = {"statusCode": 200, "body": json.dumps(result)}
            else:
                logger.error(
                    "Supported exchanges are: NYMEX, COMEX, CBOT, CBOT_MINI, CME, ICE, OANDA, COINBASE"
                )
                response = {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "error": f"Unsupported exchange: {exchange}",
                            "supported_exchanges": [
                                "NYMEX",
                                "COMEX",
                                "CBOT",
                                "CME",
                                "ICE",
                                "OANDA",
                                "COINBASE",
                            ],
                        }
                    ),
                }
        else:
            response = {
                "statusCode": 404,
                "body": json.dumps({"error": "Endpoint not found"}),
            }

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        response = {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON payload"}),
        }

    except TradingWebhookError as e:
        logger.error(f"Trading webhook error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        response = {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": str(e),
                    "error_type": "TradingWebhookError",
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        response = {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Internal server error", "request_id": request_id}
            ),
        }
