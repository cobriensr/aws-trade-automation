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
    get_position,
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
    """Generic Lambda invocation with enhanced error handling"""
    start_time = time.time()
    try:
        logger.info(f"Invoking Lambda function: {function_name}")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload) if payload else "{}"
        )

        duration = (time.time() - start_time) * 1000
        publish_metric(f"{function_name}_duration", duration, "Milliseconds")

        if response["StatusCode"] != 200:
            logger.error(f"Lambda invocation failed with status code: {response['StatusCode']}")
            raise TradingWebhookError(f"Lambda invocation failed: {response['StatusCode']}")

        payload = json.loads(response["Payload"].read())
        if "errorMessage" in payload:
            logger.error(f"Lambda execution failed with error: {payload['errorMessage']}")
            raise TradingWebhookError(f"Lambda execution failed: {payload['errorMessage']}")

        logger.info(f"Successfully invoked Lambda function: {function_name}")
        return payload

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS Lambda ClientError: {error_code} - {error_message}")
        publish_metric(f"{function_name}_error")
        raise TradingWebhookError(f"Failed to invoke {function_name}: {error_code} - {error_message}") from e
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

        actions = {
            (True, "LONG"): lambda: (
                close_short_position(
                    account_id=account, instrument=symbol, access_token=secret
                ),
                create_long_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                ),
            ),
            (True, "SHORT"): lambda: (
                close_long_position(
                    account_id=account, instrument=symbol, access_token=secret
                ),
                create_short_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                ),
            ),
            (False, "LONG"): lambda: create_long_market_order(
                account_id=account, instrument=symbol, access_token=secret
            ),
            (False, "SHORT"): lambda: create_short_market_order(
                account_id=account, instrument=symbol, access_token=secret
            ),
        }

        action = actions.get((has_position, signal_direction))
        if action:
            action()
            publish_metric("oanda_trade_success")
            return {"status": "success", "message": "Order executed successfully"}

        raise TradingWebhookError(
            f"Invalid position/direction combination: {has_position}/{signal_direction}"
        )

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
        lambda2_function_name = os.environ['LAMBDA2_FUNCTION_NAME']
        mapping_dict = invoke_lambda_function(lambda2_function_name)
        if symbol not in mapping_dict:
            raise TradingWebhookError(f"Symbol not found in mapping: {symbol}")

        mapped_symbol = mapping_dict[symbol]
        logger.info(f"Mapped symbol {symbol} to {mapped_symbol}")

        # Get account and position
        account = get_accounts(access_token)
        account_id, contract_id, net_position = get_position(
            token=access_token, instrument=mapped_symbol
        )

        # Execute trading logic based on position and signal
        if not all([account_id, contract_id, net_position]):
            logger.info(f"No existing position found for {mapped_symbol}")
            if signal_direction == "LONG":
                logger.info(f"Opening new LONG position for {mapped_symbol}")
                place_buy_order(
                    username=username,
                    instrument=mapped_symbol,
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
            if signal_direction == "SHORT":
                logger.info(f"Opening new SHORT position for {mapped_symbol}")
                place_sell_order(
                    username=username,
                    instrument=mapped_symbol,
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
        elif net_position > 0:
            logger.info(f"Existing LONG position found for {mapped_symbol}")
            if signal_direction == "SHORT":
                logger.info(
                    f"Liquidating LONG position and opening SHORT for {mapped_symbol}"
                )
                liquidate_position(
                    contract_id=contract_id, account_id=account_id, token=access_token
                )
                place_sell_order(
                    username=username,
                    instrument=mapped_symbol,
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
            if signal_direction == "LONG":
                logger.info(f"LONG position already exists for {mapped_symbol}")
                return {"status": "skipped", "message": "Position already exists"}
        elif net_position < 0:
            logger.info(f"Existing SHORT position found for {mapped_symbol}")
            if signal_direction == "LONG":
                logger.info(
                    f"Liquidating SHORT position and opening LONG for {mapped_symbol}"
                )
                liquidate_position(
                    contract_id=contract_id, account_id=account_id, token=access_token
                )
                place_buy_order(
                    username=username,
                    instrument=mapped_symbol,
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
            if signal_direction == "SHORT":
                logger.info(f"SHORT position already exists for {mapped_symbol}")
                return {"status": "skipped", "message": "Position already exists"}

        publish_metric("futures_trade_success")
        return {"status": "success", "message": "Futures trade executed successfully"}

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
        required_env_vars = ['LAMBDA2_FUNCTION_NAME']
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

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
                result = invoke_lambda_function("coinbase", webhook_data)
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
