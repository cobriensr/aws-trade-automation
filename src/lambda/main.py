"""Main Lambda function."""

import os
import json
import logging
from typing import Dict, Tuple
from pathlib import Path
import boto3
from dotenv import load_dotenv
from aws_lambda_typing.events import APIGatewayProxyEventV2
from aws_lambda_typing.context import Context
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
    get_historical_data_dict,
    get_position,
    get_accounts,
    liquidate_position,
    place_buy_order,
    place_sell_order,
)


def get_credentials() -> Tuple[str, str, str]:
    """Get credentials from either Parameter Store or .env file"""
    # First try to get from Parameter Store (production)
    try:
        ssm = boto3.client("ssm")
        secret = ssm.get_parameter(Name="/tradovate/OANDA_SECRET", WithDecryption=True)[
            "Parameter"
        ]["Value"]
        account = ssm.get_parameter(
            Name="/tradovate/OANDA_ACCOUNT", WithDecryption=True
        )["Parameter"]["Value"]
        api_secret = ssm.get_parameter(
            Name="/tradovate/DATABENTO_API_KEY", WithDecryption=True
        )["Parameter"]["Value"]
        username = ssm.get_parameter(Name="/tradovate/USERNAME", WithDecryption=True)[
            "Parameter"
        ]["Value"]

        password = ssm.get_parameter(Name="/tradovate/PASSWORD", WithDecryption=True)[
            "Parameter"
        ]["Value"]

        device_id = ssm.get_parameter(Name="/tradovate/DEVICE_ID", WithDecryption=True)[
            "Parameter"
        ]["Value"]

        cid = ssm.get_parameter(Name="/tradovate/CID", WithDecryption=True)[
            "Parameter"
        ]["Value"]

        tradovate_secret = ssm.get_parameter(
            Name="/tradovate/SECRET", WithDecryption=True
        )["Parameter"]["Value"]
        return (
            secret,
            account,
            api_secret,
            username,
            password,
            device_id,
            cid,
            tradovate_secret,
        )
    except Exception as exc:
        # If Parameter Store fails, try local .env (development)
        load_dotenv(Path(__file__).parents[2] / ".env")
        secret = os.getenv("OANDA_SECRET")
        account = os.getenv("OANDA_ACCOUNT")
        api_secret = os.getenv("DATABENTO_API_KEY")
        if not secret or not account:
            raise ValueError(
                "Could not load credentials from Parameter Store or .env"
            ) from exc
        return secret, account, api_secret


# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production


def configure_logger(context: Context) -> None:
    """Configure logger with Lambda context information"""
    formatter = logging.Formatter(
        "[%(levelname)s] %(asctime)s.%(msecs)03d "
        f"RequestId: {context.aws_request_id} "
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Clear any existing handlers
    logger.handlers.clear()

    # Add handler with formatter
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)

    # Add context information
    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")


def lambda_handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    # Configure logging at the start of execution
    configure_logger(context)

    # Log the entire event for debugging
    logger.debug(f"Full event: {json.dumps(event, indent=2)}")

    # Get credentials at the start of execution
    (
        secret,
        account,
        api_secret,
        username,
        password,
        device_id,
        cid,
        tradovate_secret,
    ) = get_credentials()

    # Get the request path from the event
    path = event.get("rawPath", event.get("path", ""))
    logger.info(f"Received request for path: {path}")

    # Check if the request is for the healthcheck endpoint
    if path == "/healthcheck" or path.endswith("/healthcheck"):
        response = {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "ok"}),
        }
        logger.info(f"Sending healthcheck response: {response}")
        return response

    # Check if the request is for the status endpoint
    if path == "/oandastatus" or path.endswith("/oandastatus"):
        account_status = check_account_status(account_id=account, access_token=secret)
        response = {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(account_status),
        }
        logger.info(f"Sending response: {response}")
        return response

    # Check if the request is for the webhook endpoint
    if path == "/webhook" or path.endswith("/webhook"):

        # Parse webhook
        webhook_data = json.loads(event["body"])

        # Parse webhook data
        signal_direction = webhook_data["signal"]["direction"]
        symbol = webhook_data["market_data"]["symbol"]
        exchange = webhook_data["market_data"]["exchange"]

        if exchange == "OANDA":
            # Check all positions
            has_position = check_position_exists(
                account_id=account, instrument=symbol, access_token=secret
            )
            if has_position is True and signal_direction == "LONG":
                # Close the open short position
                close_short_position(
                    account_id=account, instrument=symbol, access_token=secret
                )
                # Open a new long position
                create_long_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                )
            if has_position is True and signal_direction == "SHORT":
                # Close the open long position
                close_long_position(
                    account_id=account, instrument=symbol, access_token=secret
                )
                # Open a new short position
                create_short_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                )
            if has_position is False and signal_direction == "LONG":
                # Open a new long position
                create_long_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                )
            if has_position is False and signal_direction == "SHORT":
                # Open a new short position
                create_short_market_order(
                    account_id=account, instrument=symbol, access_token=secret
                )
            return {
                "statusCode": 200,
                "body": json.dumps("Webhook processed successfully"),
            }
        if exchange in ["NYMEX", "COMEX", "CBOT", "CME", "ICE"]:
            try:
                access_token, expiration_time = get_auth_token(
                    username=username,
                    password=password,
                    device_id=device_id,
                    cid=cid,
                    secret=tradovate_secret,
                )
                if access_token is None:
                    print(
                        "Failed to get access token - captcha required or authentication failed"
                    )
                else:
                    print(
                        f"Successfully obtained access token. Expires at: {expiration_time}"
                    )
            except Exception as e:
                print(f"Error getting auth token: {e}")
            # Get the mapping of symbols to instrument names
            mapping_dict = get_historical_data_dict(api_key=api_secret)
            # Get the account id
            account = get_accounts(access_token)
            # Get the position for the symbol
            account_id, contract_id, net_position = get_position(
                token=access_token, instrument=mapping_dict[symbol]
            )
            # If the position does not exist
            if not all([account_id, contract_id, net_position]):
                if signal_direction == "LONG":
                    # Place a buy order
                    place_buy_order(
                        username=username,
                        instrument=mapping_dict[symbol],
                        account_id=account,
                        quantity=1,
                        token=access_token,
                    )
                if signal_direction == "SHORT":
                    # Place a sell order
                    place_sell_order(
                        username=username,
                        instrument=mapping_dict[symbol],
                        account_id=account,
                        quantity=1,
                        token=access_token,
                    )
            if net_position > 0 and signal_direction == "SHORT":
                # Liquidate the position
                liquidate_position(
                    contract_id=contract_id, account_id=account_id, token=access_token
                )
                # Place a sell order
                place_sell_order(
                    username=username,
                    instrument=mapping_dict[symbol],
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
            if net_position > 0 and signal_direction == "LONG":
                return {
                    "statusCode": 200,
                    "body": json.dumps("Position already exists"),
                }
            if net_position < 0 and signal_direction == "LONG":
                # Liquidate the position
                liquidate_position(
                    contract_id=contract_id, account_id=account_id, token=access_token
                )
                # Place a buy order
                place_buy_order(
                    username=username,
                    instrument=mapping_dict[symbol],
                    account_id=account,
                    quantity=1,
                    token=access_token,
                )
            if net_position < 0 and signal_direction == "SHORT":
                return {
                    "statusCode": 200,
                    "body": json.dumps("Position already exists"),
                }
            return {
                "statusCode": 200,
                "body": json.dumps("Webhook processed successfully"),
            }
        return {
            "statusCode": 400,
            "body": json.dumps("Cryptocurrency exchange not supported"),
        }
