"""Secondary Lambda function for symbol lookup."""

import os
import json
import logging
from typing import Dict
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
import boto3
import databento as db
from aws_lambda_typing.events import APIGatewayProxyEventV2
from aws_lambda_typing.context import Context

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def configure_logger(context: Context) -> None:
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

def get_api_key() -> str:
    """Get Databento API key from Parameter Store"""
    try:
        ssm = boto3.client("ssm")
        api_key = ssm.get_parameter(
            Name="/tradovate/DATABENTO_API_KEY",
            WithDecryption=True
        )["Parameter"]["Value"]
        return api_key
    except Exception as exc:
        # If Parameter Store fails, try local .env (development)
        load_dotenv(Path(__file__).parents[2] / ".env")
        api_key = os.getenv("DATABENTO_API_KEY")
        if not api_key:
            raise ValueError(
                "Could not load credentials from Parameter Store or .env"
            ) from exc
        return api_key

def get_historical_data_dict(api_key: str) -> Dict:
    """Get historical data and return symbol mapping dictionary"""
    # Retrieve yesterday's and today's date in the format required by the API
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    data_start = yesterday.strftime("%Y-%m-%d")
    data_end = today.strftime("%Y-%m-%d")

    # Create a client instance
    db_client = db.Historical(api_key)

    # Mapping of symbol names to the ones used in the API
    symbol_mapping = {
        "MES.n.0": "MES1!",
        "MNQ.n.0": "MNQ1!",
        "YM.n.0": "YM1!",
        "RTY.n.0": "RTY1!",
        "NG.n.0": "NG1!",
        "GC.n.0": "GC1!",
        "CL.n.0": "CL1!",
    }
    
    try:
        # Get historical data for the specified symbols
        df = db_client.timeseries.get_range(
            dataset="GLBX.MDP3",
            schema="definition",
            stype_in="continuous",
            symbols=list(symbol_mapping.keys()),
            start=data_start,
            end=data_end,
        ).to_df()
        
        # Extract the date and symbol columns
        df["date"] = df.index.date
        # Pivot the data to have symbols as columns
        pivoted = df.pivot(index="date", columns="symbol", values="raw_symbol")

        # Get just the latest row and convert to simple dictionary
        latest_data = pivoted.iloc[-1].to_dict()
        # Map the symbol names to the ones used in the API
        return {symbol_mapping[k]: v for k, v in latest_data.items()}
    except Exception as exc:
        logger.error(f"Failed to get historical data: {exc}")
        raise

def lambda_handler(event: APIGatewayProxyEventV2, context: Context) -> Dict:
    """Lambda handler for symbol lookup."""
    configure_logger(context)
    logger.debug(f"Received event: {json.dumps(event, indent=2)}")
    
    try:
        # Get API key from Parameter Store
        api_key = get_api_key()
        
        # Get symbol mapping
        symbol_mapping = get_historical_data_dict(api_key)
        
        return {
            "statusCode": 200,
            "body": json.dumps(symbol_mapping)
        }
    except Exception as exc:
        logger.error(f"Error processing request: {exc}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(exc)})
        }