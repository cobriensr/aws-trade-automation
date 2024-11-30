"""Main Lambda function."""
import os
import json
import logging
import asyncio
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
    create_short_market_order
)

def get_credentials() -> Tuple[str, str]:
    """Get credentials from either Parameter Store or .env file"""
    # First try to get from Parameter Store (production)
    try:
        ssm = boto3.client('ssm')
        secret = ssm.get_parameter(Name='/tradovate/OANDA_SECRET', WithDecryption=True)['Parameter']['Value']
        account = ssm.get_parameter(Name='/tradovate/OANDA_ACCOUNT', WithDecryption=True)['Parameter']['Value']
        return secret, account
    except Exception as exc:
        # If Parameter Store fails, try local .env (development)
        load_dotenv(Path(__file__).parents[2] / ".env")
        secret = os.getenv("OANDA_SECRET")
        account = os.getenv("OANDA_ACCOUNT")
        if not secret or not account:
            raise ValueError("Could not load credentials from Parameter Store or .env") from exc
        return secret, account

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production

def configure_logger(context: Context) -> None:
    """Configure logger with Lambda context information"""
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s.%(msecs)03d '
        f'RequestId: {context.aws_request_id} '
        '%(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Add handler with formatter
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Add context information
    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")

async def lambda_handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    # Configure logging at the start of execution
    configure_logger(context)
    
    # Get credentials at the start of execution
    secret, account = get_credentials()
    
    # Get the request path from the event
    path = event.get('path', '')

    # Check if the request is for the healthcheck endpoint
    if path == '/healthcheck':
        return {
            'statusCode': 200,
            'body': json.dumps('ok')
        }
    
    # Check if the request is for the status endpoint
    if path == '/oandastatus':
        account_status = check_account_status(
            account_id=account,
            access_token=secret
        )
        return {
            'statusCode': 200,
            'body': json.dumps(account_status)
        }
    
    # Check if the request is for the webhook endpoint
    if path == '/webhook':
    
        # Parse webhook
        webhook_data = event['body']
        
        # Parse webhook data
        signal_direction = webhook_data['signal']['direction']
        symbol = webhook_data['market_data']['symbol']
        exchange = webhook_data['market_data']['exchange']
        
        if exchange == 'OANDA':
            # Usage example:
            has_position = check_position_exists(
            account_id=account,
            instrument=symbol,
            access_token=secret
            )
            if has_position is True and signal_direction == 'LONG':
                # Close the open short position
                close_short_position(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
                # Open a new long position
                create_long_market_order(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
            if has_position is True and signal_direction == 'SHORT':
                # Close the open long position
                close_long_position(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
                # Open a new short position
                create_short_market_order(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
            if has_position is False and signal_direction == 'LONG':
                # Open a new long position
                create_long_market_order(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
            if has_position is False and signal_direction == 'SHORT':
                # Open a new short position
                create_short_market_order(
                    account_id=account,
                    instrument=symbol,
                    access_token=secret
                )
        return {
            'statusCode': 200,
            'body': json.dumps('Webhook processed successfully')
        }

def handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(lambda_handler(event, context))