"""Main Lambda function for tradingview webhooks."""

import os
import json
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Dict, Tuple, Any
import psutil
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
    get_contract_info,
    get_accounts,
    get_cash_balance_snapshot,
    liquidate_position,
    place_buy_order,
    place_sell_order,
)

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")
lambda_client = boto3.client("lambda")

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production


class TradingWebhookError(Exception):
    """Custom exception for webhook processing errors"""


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

        # Get symbol mapping
        lambda2_function_name = os.environ["LAMBDA2_FUNCTION_NAME"]
        mapping_response = invoke_lambda_function(lambda2_function_name)

        try:
            response_body = json.loads(mapping_response.get("body", "{}"))
            mapping_dict = response_body.get("data", {})
            logger.info(f"Received symbol mapping: {json.dumps(mapping_dict)}")

            if symbol not in mapping_dict:
                raise TradingWebhookError(f"Symbol not found in mapping: {symbol}")

            mapped_symbol = mapping_dict[symbol]
            logger.info(f"Mapped symbol {symbol} to {mapped_symbol}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse symbol mapping response: {str(e)}")
            raise TradingWebhookError("Invalid symbol mapping response format") from e
        except KeyError as e:
            logger.error(f"Missing required field in symbol mapping response: {str(e)}")
            raise TradingWebhookError(
                "Invalid symbol mapping response structure"
            ) from e

        # Get default account ID first
        account_id = get_accounts(access_token)

        # Get current positions
        positions = get_all_positions(access_token, mapped_symbol)

        if positions:
            # There are existing positions - liquidate and then place new order
            logger.info(
                f"Found existing positions for {mapped_symbol}, liquidating first"
            )
            contracts_ids = [position["contractId"] for position in positions]
            contract_names_with_ids = get_contract_info(
                token=access_token, contract_ids=contracts_ids
            )

            for contract in contract_names_with_ids:
                if mapped_symbol in contract["contractName"]:
                    liquidate_result = liquidate_position(
                        contract_id=contract["contractId"],
                        account_id=account_id,
                        token=access_token,
                    )
                    logger.info(f"Liquidation result: {liquidate_result}")

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
    """Main Lambda handler with comprehensive error handling and logging"""
    request_id = context.aws_request_id
    start_time = time.time()
    response = None

    try:
        # Configure logging
        configure_logger(context)

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

        # Handle different endpoints
        if path.endswith("/healthcheck"):
            response = {"statusCode": 200, "body": json.dumps({"status": "healthy"})}
            return response

        if path.endswith("/oandastatus"):
            status = check_account_status(account_id=creds[1], access_token=creds[0])
            response = {"statusCode": 200, "body": json.dumps(status)}
            return response

        if path.endswith("/tradovatestatus"):
            token, _ = get_auth_token(
                username=creds[2],
                password=creds[3],
                device_id=creds[4],
                cid=creds[5],
                secret=creds[6],
            )
            account_id = get_accounts(token)
            balance = get_cash_balance_snapshot(token, account_id)
            response = {"statusCode": 200, "body": json.dumps(balance)}
            return response

        if path.endswith("/webhook"):
            webhook_data = json.loads(event["body"])
            signal_direction = webhook_data["signal"]["direction"]
            symbol = webhook_data["market_data"]["symbol"]
            exchange = webhook_data["market_data"]["exchange"]

            logger.info(f"Processing webhook: {exchange} {symbol} {signal_direction}")
            publish_metric(f"{exchange.lower()}_webhook_received")

            if exchange == "COINBASE":
                result = invoke_lambda_function("trading-prod-coinbase", webhook_data)

                # If result already contains statusCode and body, return it directly
                if (
                    isinstance(result, dict)
                    and "statusCode" in result
                    and "body" in result
                ):
                    logger.info(
                        f"Propagating Coinbase Lambda response with status {result['statusCode']}"
                    )
                    return result

                # Otherwise, wrap the result in a 200 response
                response = {"statusCode": 200, "body": json.dumps(result)}
                return response

            if exchange == "OANDA":
                result = handle_oanda_trade(
                    creds[1], symbol, signal_direction, creds[0]
                )
                response = {"statusCode": 200, "body": json.dumps(result)}
                return response

            if exchange in ["NYMEX", "COMEX", "CBOT", "CME", "ICE"]:
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
                return response

            response = {
                "statusCode": 400,
                "body": json.dumps({"error": "Unsupported exchange"}),
            }
            return response

        response = {
            "statusCode": 404,
            "body": json.dumps({"error": "Endpoint not found"}),
        }
        return response

    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        response = {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON payload"}),
        }
        return response

    except TradingWebhookError as e:
        logger.error(f"Trading webhook error: {str(e)}")
        response = {"statusCode": 400, "body": json.dumps({"error": str(e)})}
        return response

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        response = {
            "statusCode": 500,
            "body": json.dumps(
                {"error": "Internal server error", "request_id": request_id}
            ),
        }
        return response

    finally:
        # Calculate duration and log completion
        duration = (time.time() - start_time) * 1000

        # Record response status code metric
        if response:
            status_code = response.get("statusCode", 500)
            publish_metric(f"status_code_{status_code}")

            # Record error metrics for non-200 responses
            if status_code >= 400:
                publish_metric("error_count")
                if status_code >= 500:
                    publish_metric("server_error_count")
                else:
                    publish_metric("client_error_count")

        # Record duration metric
        publish_metric("request_duration", duration, "Milliseconds")

        # Log request completion with relevant details
        log_message = (
            f"Request {request_id} completed in {duration:.2f}ms "
            f"with status {response['statusCode'] if response else 'unknown'}"
        )
        if duration > 5000:  # Log warning for slow requests
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)

        # Track remaining Lambda execution time
        remaining_time = context.get_remaining_time_in_millis()
        if remaining_time < 1000:  # Log warning if less than 1 second remaining
            logger.warning(f"Low remaining execution time: {remaining_time}ms")

        # Record memory usage
        try:
            memory_used = (
                psutil.Process().memory_info().rss / 1024 / 1024
            )  # Convert to MB
            publish_metric("memory_used", memory_used, "Megabytes")
            memory_limit = float(context.memory_limit_in_mb)  # Convert to float
            threshold = int(memory_limit * 0.9)  # Convert the threshold to integer
            if memory_used > threshold:
                logger.warning(f"High memory usage: {memory_used:.2f}MB")
        except ImportError:
            logger.warning("psutil not available - memory monitoring disabled")
        except Exception as e:
            logger.error(f"Error monitoring memory usage: {str(e)}")
