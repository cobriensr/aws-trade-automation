"""
Unified cache management system for Tradovate and symbol lookup using DynamoDB.
This module provides a centralized caching solution with consistent TTL handling,
error management, and logging across different Lambda functions.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Optional, Dict, Any
import json
import boto3
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()


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
