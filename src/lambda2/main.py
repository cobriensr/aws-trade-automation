"""Secondary Lambda function for symbol lookup with enhanced caching and monitoring."""

import os
import json
import logging
import time
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError
import boto3
import databento as db

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
cloudwatch = boto3.client("cloudwatch")
ssm = boto3.client("ssm")
cloudwatch_namespace = "Trading/SymbolLookup"

# Cache configuration from environment variables with defaults
CACHE_TABLE_NAME = os.environ.get("CACHE_TABLE_NAME", "trading-prod-tradovate-cache")
CACHE_FAILURE_THRESHOLD = int(os.environ.get("CACHE_FAILURE_THRESHOLD", "3"))
cache_failures = 0  # Track consecutive cache failures for circuit breaker

class TradingCache:
    """
    Manages both Tradovate and symbol lookup data caching using DynamoDB.
    This class provides a unified interface for all caching operations across
    the trading system.
    """

    def __init__(self, table_name: str = "trading-prod-tradovate-cache"):
        """
        Initialize the cache manager with DynamoDB connection.

        Args:
            table_name (str): Name of the DynamoDB table to use for caching.
                            Defaults to production table name.
        """
        try:
            # Initialize DynamoDB client
            self.dynamodb = boto3.resource("dynamodb")
            logger.info("Successfully initialized DynamoDB resource")

            # Get reference to the cache table
            self.table = self.dynamodb.Table(table_name)

            # Verify table connection by checking status
            table_status = self.table.table_status
            logger.info(
                f"Successfully connected to DynamoDB table: {table_name} (Status: {table_status})"
            )

            # Cache configuration constants
            self.ACCOUNT_CACHE_KEY = "ACCOUNT_INFO"
            self.SYMBOL_CACHE_PREFIX = "symbol_mapping:"
            self.CACHE_TTL_HOURS = 18  # Set to 18 hours for symbol mappings

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            error_message = e.response.get("Error", {}).get("Message")
            logger.error(
                f"DynamoDB initialization error: {error_code} - {error_message}"
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing DynamoDB connection: {str(e)}")
            raise

    def get_cached_symbol(self, continuous_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached symbol mapping from DynamoDB if it exists and is not expired.

        Args:
            continuous_symbol (str): The continuous contract symbol (e.g., 'ES1!')

        Returns:
            Optional[Dict]: Cached mapping data if found and valid, None otherwise
        """
        try:
            # Construct the cache key for this symbol
            cache_key = f"{self.SYMBOL_CACHE_PREFIX}{continuous_symbol}"

            # Attempt to retrieve the item from DynamoDB
            response = self.table.get_item(Key={"cache_key": cache_key})

            # If no item found, return None
            if "Item" not in response:
                logger.info(f"No cache entry found for {continuous_symbol}")
                return None

            item = response["Item"]
            current_time = int(datetime.now(timezone.utc).timestamp())

            # Check if the cached item has expired
            if "ttl" in item and item["ttl"] < current_time:
                logger.info(f"Cache expired for {continuous_symbol}")
                return None

            # Return the cached data if it exists
            if "cache_data" in item:
                return json.loads(item["cache_data"])
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def cache_symbol_mapping(self, continuous_symbol: str, actual_symbol: str) -> bool:
        """
        Store symbol mapping in DynamoDB cache with configured TTL.

        Args:
            continuous_symbol (str): The continuous contract symbol (e.g., 'ES1!')
            actual_symbol (str): The actual contract symbol (e.g., 'ESH5')

        Returns:
            bool: True if caching was successful, False otherwise
        """
        try:
            # Construct the cache key
            cache_key = f"{self.SYMBOL_CACHE_PREFIX}{continuous_symbol}"
            current_time = datetime.now(timezone.utc)

            # Prepare the data to be cached
            cache_data = {
                "continuous_symbol": continuous_symbol,
                "actual_symbol": actual_symbol,
                "cached_at": current_time.isoformat(),
            }

            # Calculate TTL timestamp
            ttl = int(
                (current_time + timedelta(hours=self.CACHE_TTL_HOURS)).timestamp()
            )

            # Store in DynamoDB with TTL
            self.table.put_item(
                Item={
                    "cache_key": cache_key,
                    "cache_data": json.dumps(cache_data),
                    "ttl": ttl,
                }
            )

            logger.info(
                f"Successfully cached mapping {continuous_symbol} -> {actual_symbol}"
            )
            return True

        except Exception as e:
            logger.error(f"Error caching symbol mapping: {str(e)}")
            return False

    def get_cached_account(self, username: str) -> Optional[int]:
        """
        Retrieve cached account ID for a Tradovate user.

        Args:
            username (str): Tradovate username

        Returns:
            Optional[int]: Cached account ID if found and valid, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={"cache_key": f"{self.ACCOUNT_CACHE_KEY}_{username}"}
            )

            if "Item" in response:
                item = response["Item"]
                current_time = int(datetime.now(timezone.utc).timestamp())

                # Check if cache is still valid
                if "ttl" in item and item["ttl"] > current_time:
                    return item["account_id"]

            return None

        except Exception as e:
            logger.error(f"Failed to get cached account: {str(e)}")
            return None

    def cache_account(self, username: str, account_id: int) -> bool:
        """
        Cache account ID for a Tradovate user.

        Args:
            username (str): Tradovate username
            account_id (int): Account ID to cache

        Returns:
            bool: True if caching was successful, False otherwise
        """
        try:
            current_time = datetime.now(timezone.utc)
            expiration = current_time + timedelta(hours=self.CACHE_TTL_HOURS)

            self.table.put_item(
                Item={
                    "cache_key": f"{self.ACCOUNT_CACHE_KEY}_{username}",
                    "account_id": account_id,
                    "username": username,
                    "cached_at": current_time.isoformat(),
                    "ttl": int(expiration.timestamp()),
                }
            )
            return True

        except Exception as e:
            logger.error(f"Failed to cache account: {str(e)}")
            return False

    def invalidate_cache(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            key (str): The cache key to invalidate. Can be username for account cache
                      or continuous symbol for symbol mapping cache.

        Returns:
            bool: True if invalidation was successful, False otherwise
        """
        try:
            # Determine the full cache key based on the input
            if key.startswith(self.SYMBOL_CACHE_PREFIX):
                cache_key = key
            else:
                cache_key = f"{self.ACCOUNT_CACHE_KEY}_{key}"

            # Delete the item from DynamoDB
            self.table.delete_item(Key={"cache_key": cache_key})
            logger.info(f"Successfully invalidated cache for key: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to invalidate cache: {str(e)}")
            return False

class SymbolLookupError(Exception):
    """Custom exception for symbol lookup errors"""


class CacheError(Exception):
    """Custom exception for cache-related errors"""

# Initialize cache manager with configured table name
cache_manager = TradingCache(table_name=CACHE_TABLE_NAME)

def publish_metric(name: str, value: float = 1, unit: str = "Count") -> None:
    """Publish a metric to CloudWatch"""
    try:
        cloudwatch.put_metric_data(
            Namespace=cloudwatch_namespace,
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

        cloudwatch.put_metric_data(Namespace=cloudwatch_namespace, MetricData=metrics)
    except Exception as e:
        logger.error(f"Error publishing concurrency metrics: {str(e)}")


def track_error_rate(has_error: bool):
    """Track error rate for the function"""
    try:
        cloudwatch.put_metric_data(
            Namespace=cloudwatch_namespace,
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
            stype_in="continuous",
            symbols=[
                "ES.n.0",
                "NQ.n.0",
                "6E.n.0",
                "GC.n.0",
                "RTY.n.0",
                "CL.n.0",
                "YM.n.0",
                "NG.n.0",
                "MBT.n.0",
                "HG.n.0",
                "SI.n.0",
            ],
            schema="ohlcv-1d",
            start=prev_bus_day,
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
            start_date=prev_bus_day,
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


def get_historical_data_dict(lookup_symbol) -> str:
    """Get historical data with comprehensive error handling, metrics, and caching"""
    global cache_failures
    cache_start_time = time.time()

    try:
        # Only try cache if we haven't had too many failures
        if cache_failures < CACHE_FAILURE_THRESHOLD:
            try:
                # Attempt to retrieve from cache
                cached_data = cache_manager.get_cached_symbol(lookup_symbol)
                cache_duration = (time.time() - cache_start_time) * 1000
                publish_metric(
                    "cache_operation_duration", cache_duration, "Milliseconds"
                )

                if cached_data is not None:
                    cache_failures = 0  # Reset failures on successful cache hit
                    logger.info(f"Cache hit for symbol {lookup_symbol}")
                    publish_metric("symbol_cache_hit")
                    return cached_data["actual_symbol"]

            except Exception as cache_error:
                cache_failures += 1
                logger.warning(
                    f"Cache failure {cache_failures}/{CACHE_FAILURE_THRESHOLD}: {str(cache_error)}"
                )
                publish_metric("cache_error")
        else:
            logger.warning(
                f"Cache bypassed due to {cache_failures} consecutive failures"
            )
            publish_metric("cache_circuit_breaker_active")

        # Log cache miss and proceed with Databento lookup
        logger.info(
            f"Cache miss for symbol {lookup_symbol}, performing Databento lookup"
        )
        publish_metric("symbol_cache_miss")

        # If not in cache or expired, perform the lookup
        top_instruments = rank_by_volume()
        symbols = match_symbol_to_rank(top_instruments)
        cleaned_list = clean_symbols(symbols)
        mapping = create_symbol_mapping(cleaned_list)
        final_symbol = output_reversed_map(mapping, lookup_symbol)

        # Attempt to cache the result if circuit breaker is not active
        if cache_failures < CACHE_FAILURE_THRESHOLD:
            try:
                cache_write_start = time.time()
                # Here's the key change: we're caching the lookup_symbol (ES1!) to map to the final_symbol (ESH5)
                cache_manager.cache_symbol_mapping(lookup_symbol, final_symbol)
                cache_write_duration = (time.time() - cache_write_start) * 1000
                publish_metric(
                    "cache_write_duration", cache_write_duration, "Milliseconds"
                )
                publish_metric("cache_write_success")
                cache_failures = 0  # Reset failures on successful write
                logger.info(f"Successfully cached mapping: {lookup_symbol} -> {final_symbol}")  # Added for clarity
            except Exception as cache_error:
                cache_failures += 1
                logger.warning(f"Failed to cache result: {str(cache_error)}")
                publish_metric("cache_write_error")

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

        # Extract symbol from event with validation
        market_data = event.get("market_data")
        if not market_data:
            raise SymbolLookupError("No market_data found in event")

        lookup_symbol = market_data.get("symbol")
        if not lookup_symbol:
            raise SymbolLookupError("No symbol found in market_data")

        # Get symbol mapping
        final_symbol = get_historical_data_dict(lookup_symbol)

        # Log symbol mapping
        logger.info(f"Symbol mapping result: {final_symbol}")

        # Record success response with detailed timing
        response = {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "success",
                    "symbol": final_symbol,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": request_id,
                    "cache_status": (
                        "bypassed"
                        if cache_failures >= CACHE_FAILURE_THRESHOLD
                        else "active"
                    ),
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
                {
                    "status": "error",
                    "error": str(e),
                    "request_id": request_id,
                    "cache_status": (
                        "bypassed"
                        if cache_failures >= CACHE_FAILURE_THRESHOLD
                        else "active"
                    ),
                }
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
                    "cache_status": (
                        "bypassed"
                        if cache_failures >= CACHE_FAILURE_THRESHOLD
                        else "active"
                    ),
                }
            ),
        }

    finally:
        # Track error rate and timing metrics
        track_error_rate(has_error)
        duration = (time.time() - start_time) * 1000
        publish_metric("request_duration", duration, "Milliseconds")

        # Enhanced request completion logging
        log_message = (
            f"Request {request_id} completed in {duration:.2f}ms "
            f"(Cache status: {'bypassed' if cache_failures >= CACHE_FAILURE_THRESHOLD else 'active'})"
        )

        if duration > 5000:
            logger.warning(f"{log_message} - Request took longer than 5 seconds")
        else:
            logger.info(log_message)

        # Monitor resources
        remaining_time = context.get_remaining_time_in_millis()
        if remaining_time < 1000:
            logger.warning(f"Low remaining execution time: {remaining_time}ms")