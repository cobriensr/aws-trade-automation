"""Secondary Lambda function for symbol lookup."""

import json
import logging
import time
import traceback
from typing import Dict, List
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
import psutil
import boto3
import databento as db

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")
ssm = boto3.client("ssm")


class SymbolLookupError(Exception):
    """Custom exception for symbol lookup errors"""


def publish_metric(name: str, value: float = 1, unit: str = "Count") -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace="Trading/SymbolLookup",
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
    """Configure logger with enhanced Lambda context information"""
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
    logger.info(f"Function Memory: {context.memory_limit_in_mb}MB")
    logger.info(f"Remaining Time: {context.get_remaining_time_in_millis()}ms")


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

        cloudwatch.put_metric_data(Namespace="Trading/SymbolLookup", MetricData=metrics)
    except Exception as e:
        logger.error(f"Error publishing concurrency metrics: {str(e)}")


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


def get_api_key() -> str:
    """Get Databento API key with enhanced error handling"""
    try:
        response = ssm.get_parameter(
            Name="/tradovate/DATABENTO_API_KEY", WithDecryption=True
        )
        key = response["Parameter"]["Value"]
        publish_metric("api_key_retrieval_success")
        return key

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"AWS SSM error retrieving API key: {error_code} - {str(e)}")
        publish_metric("api_key_retrieval_error")
        raise SymbolLookupError(
            "Failed to retrieve Databento API key from all sources"
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error retrieving API key: {str(e)}")
        publish_metric("api_key_retrieval_error")
        raise SymbolLookupError(f"API key retrieval failed: {str(e)}") from e


def get_today():
    """
    Returns today's date in YYYY-MM-DD format

    Returns:
        str: Today's date in YYYY-MM-DD format
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_previous_business_day(date=None):
    """
    Returns the business day before the previous business day (Monday-Friday) in YYYY-MM-DD format.
    If no date is provided, uses current date.

    Args:
        date (datetime, optional): Input date. Defaults to None (current date).

    Returns:
        str: Business day before the previous business day in YYYY-MM-DD format
    """
    # If no date provided, use current date
    if date is None:
        date = datetime.now()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")

    # Start with previous day
    prev_day = date - timedelta(days=2)  # Changed from 1 to 2 to go back an extra day

    # Keep going back until we find a business day - 5 = Saturday, 6 = Sunday
    while prev_day.weekday() >= 5:
        prev_day -= timedelta(days=1)

    return prev_day.strftime("%Y-%m-%d")


# Get dates for queries
prev_bus_day = get_previous_business_day()
today = get_today()

# Initialize Databento client with timeout handling
api_key = get_api_key()
db_client = db.Historical(api_key)


def extract_base_symbol(symbol):
    """
    Extract base symbol from a futures contract symbol.

    Args:
        symbol (str): Futures contract symbol (e.g., 'MESH5', 'ESH5', 'ZNH5')

    Returns:
        str: Base symbol without expiration (e.g., 'MES', 'ES', 'ZN')
    """
    # Remove any spaces and anything after them (for options symbols like 'E3DZ4 P4800')
    symbol = symbol.split()[0]

    # Specific mappings for known products
    if symbol.startswith(
        ("MES", "MNQ", "M2K", "MGC", "MBT", "MET", "MCL", "MYM")
    ):  # Micro products
        return symbol[:3]
    elif symbol.startswith("6"):  # Currency futures
        return symbol[:2]
    elif symbol.startswith(
        ("ZN", "ZB", "ZF", "ZT", "ZC", "ZS", "ZQ", "ZW", "ZL", "ZM")
    ):  # Z- products
        return (
            symbol[:2] if not symbol.startswith("ZM") else "ZM"
        )  # Special handling for ZM
    elif symbol.startswith(
        (
            "ES",
            "NQ",
            "NG",
            "CL",
            "GC",
            "SI",
            "HG",
            "TN",
            "UB",
            "YM",
            "KC",
            "KE",
            "RB",
            "PL",
        )
    ):  # Common two-letter products
        return symbol[:2]
    elif symbol.startswith(("RTY", "SR3", "SR1")):  # Three-letter products
        if symbol.startswith("SR"):  # Special handling for SR products
            return "SR3" if symbol.startswith("SR3") else "SR1"
        return symbol[:3]
    else:
        # Find where the expiration month starts
        for i, char in enumerate(symbol):
            if char.isdigit() or char in [
                "F",
                "G",
                "H",
                "J",
                "K",
                "M",
                "N",
                "Q",
                "U",
                "V",
                "X",
                "Z",
            ]:
                if i > 0:  # Make sure we don't return empty string
                    return symbol[:i]
        # If no clear break found, default to first two characters
        return symbol[:2]


def rank_by_volume(top=100) -> List[int]:
    """
    Get top volume instruments from Databento.

    Args:
        top (int): Number of top instruments to return. Defaults to 50.

    Returns:
        List[int]: List of instrument IDs sorted by volume
    """
    try:
        data = db_client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols="[/ >rhj<gF]",
            schema="ohlcv-1d",
            start=prev_bus_day
        )
        df = data.to_df()
        return df.sort_values(by="volume", ascending=False).instrument_id.tolist()[:top]
    except Exception as e:
        logger.error(f"Error fetching volume data: {e}")
        raise


def match_symbol_to_rank(instrument_ids: List[int]) -> str:
    """
    Convert instrument IDs to symbols using Databento API.

    Args:
        instrument_ids (List[int]): List of instrument IDs

    Returns:
        str: Symbol mapping data from Databento
    """
    try:
        data = db_client.symbology.resolve(
            dataset="GLBX.MDP3",
            symbols=[instrument_ids],
            stype_in="instrument_id",
            stype_out="raw_symbol",
            start_date=prev_bus_day
        )
        return data
    except Exception as e:
        logger.error(f"Error resolving symbols: {e}")
        raise


def clean_symbols(trade_symbols):
    """
    Clean and deduplicate symbols list.

    Args:
        trade_symbols (dict): Symbol data from Databento

    Returns:
        List[str]: Cleaned list of symbols
    """
    # Extract symbols while preserving order
    sym_list = [item[0]["s"] for item in trade_symbols["result"].values()]

    # Remove symbols with hyphens
    clean = [s for s in sym_list if "-" not in s]

    # Track seen base symbols to avoid duplicates
    seen_bases = set()
    result = []

    for symbol in clean:
        base = extract_base_symbol(symbol)

        # If we haven't seen this base symbol yet, keep it
        if base not in seen_bases:
            seen_bases.add(base)
            result.append(symbol)

    return result


def create_symbol_mapping(cleaned_symbols):
    """
    Create mapping between actual contracts and continuous symbols.

    Args:
        cleaned_symbols (List[str]): List of cleaned symbols

    Returns:
        dict: Mapping of actual contracts to continuous symbols
    """
    # Dictionary to store the mappings
    databento_mapping = {}

    for symbol in cleaned_symbols:
        base = extract_base_symbol(symbol)
        # Create continuous contract symbol (base + "1!")
        continuous_symbol = f"{base}1!"
        # Add to mapping (actual contract: continuous contract)
        databento_mapping[symbol] = continuous_symbol

    return databento_mapping


def output_reversed_map(mapped_items, webhook_symbol):
    """
    Find actual contract symbol from continuous contract symbol.

    Args:
        mapped_items (dict): Symbol mapping dictionary
        webhook_symbol (str): Continuous contract symbol (e.g., 'MES1!')

    Returns:
        str: Actual contract symbol (e.g., 'MESH5')

    Raises:
        ValueError: If no matching contract is found
    """
    reverse_mapping = {v: k for k, v in mapped_items.items()}
    actual_contract = reverse_mapping.get(webhook_symbol)

    if actual_contract is None:
        error_msg = f"No matching contract found for {webhook_symbol}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    return actual_contract


def get_historical_data_dict(lookup_symbol) -> Dict:
    """Get historical data with comprehensive error handling and metrics"""
    start_time = time.time()
    try:
        top_instruments = rank_by_volume()
        symbols = match_symbol_to_rank(top_instruments)
        cleaned_list = clean_symbols(symbols)
        mapping = create_symbol_mapping(cleaned_list)
        final_symbol = output_reversed_map(mapping, lookup_symbol)

        # Record success metrics
        duration = (time.time() - start_time) * 1000
        publish_metric("databento_request_duration", duration, "Milliseconds")
        publish_metric("databento_request_success")
        publish_metric("symbols_mapped", len(mapping))
        return final_symbol

    except Exception as e:
        publish_metric("symbol_lookup_error")
        logger.error(f"Symbol lookup error: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        raise SymbolLookupError(f"Failed to get historical data: {str(e)}") from e


def lambda_handler(event, context) -> Dict:
    """Lambda handler with comprehensive error handling and monitoring"""
    request_id = context.aws_request_id
    start_time = time.time()
    has_error = False

    try:
        # Track concurrent executions at start
        monitor_concurrent_executions()

        # Configure logging
        configure_logger(context)
        logger.info(f"Processing request {request_id}")
        logger.debug(f"Event: {json.dumps(event, indent=2)}")

        # Extract symbol from event
        lookup_symbol = event.get("market_data").get("symbol")

        # Get symbol mapping
        final_symbol = get_historical_data_dict(lookup_symbol)

        # Log symbol mapping
        logger.info(f"Symbol mapping result: {final_symbol}")

        # Record success response
        response = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "success",
                    "symbol": final_symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            ),
        }

        # Log response
        logger.info(f"Returning response: {json.dumps(response)}")

        return response

    except SymbolLookupError as e:
        has_error = True
        logger.error(f"Symbol lookup error in request {request_id}: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps(
                {"status": "error", "error": str(e), "request_id": request_id}
            ),
        }

    except Exception as e:
        has_error = True
        logger.error(f"Unexpected error in request {request_id}: {str(e)}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "status": "error",
                    "error": "Internal server error",
                    "request_id": request_id,
                }
            ),
        }

    finally:
        # Track error rate
        track_error_rate(has_error)

        # Calculate and record duration
        duration = (time.time() - start_time) * 1000
        publish_metric("request_duration", duration, "Milliseconds")

        # Log request completion
        log_message = f"Request {request_id} completed in {duration:.2f}ms"
        if duration > 5000:
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)

        # Monitor resources
        remaining_time = context.get_remaining_time_in_millis()
        if remaining_time < 1000:
            logger.warning(f"Low remaining execution time: {remaining_time}ms")

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
