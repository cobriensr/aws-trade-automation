"""Main Lambda function."""
import os
import json
import logging
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
from aws_lambda_typing import Context
from aws_lambda_typing.events import APIGatewayProxyEventV2
from .trading.oanda import check_position_exists, close_long_position, close_short_position, create_long_market_order, create_short_market_order

# Use relative path navigation
load_dotenv(Path(__file__).parents[2] / ".env")

secret = os.getenv("OANDA_SECRET")
account = os.getenv("OANDA_ACCOUNT")

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
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Add context information
    logger.info(f"Log Group: {context.log_group_name}")
    logger.info(f"Log Stream: {context.log_stream_name}")

async def lambda_handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    # Configure logging at the start of execution
    configure_logger(context)
    
    # Get the request path from the event
    path = event.get('path', '')

    # Check if the request is for the healthcheck endpoint
    if path == '/healthcheck':
        return {
            'statusCode': 200,
            'body': json.dumps('ok')
        }
    
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

#     {
#     "action": "LONG_ENTRY",
#     "indicator": "Trend_Validator",
#     "signal": {
#       "type": "ENTRY",
#       "direction": "LONG",
#       "trigger": "COLOR_CHANGE_BLUE"
#     },
#     "market_data": {
#       "symbol": "USDCHF",
#       "exchange": "OANDA",
#       "timeframe": "10",
#       "timestamp": "2024-11-28T21:20:00Z",
#       "timenow": "2024-11-28T21:30:01Z"
#     },
#     "price_data": {
#       "open": "0.88294",
#       "high": "0.88298",
#       "low": "0.8829",
#       "close": "0.88298",
#       "volume": "46"
#     }
#   }
