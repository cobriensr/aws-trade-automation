"""Tradovate cache management with DynamoDB."""

from datetime import datetime, timezone, timedelta
import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


class TradovateCache:
    """Manages Tradovate data caching using DynamoDB."""

    def __init__(self, table_name: str = "trading-prod-tradovate-cache"):
        try:
            self.dynamodb = boto3.resource("dynamodb")
            logger.info("Successfully initialized DynamoDB resource")
            
            self.table = self.dynamodb.Table(table_name)
            # Test the table connection by checking its status
            table_status = self.table.table_status
            logger.info(f"Successfully connected to DynamoDB table: {table_name} (Status: {table_status})")
            
            self.ACCOUNT_CACHE_KEY = "ACCOUNT_INFO"
            self.CACHE_TTL_HOURS = 12
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            error_message = e.response.get('Error', {}).get('Message')
            logger.error(f"DynamoDB initialization error: {error_code} - {error_message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error initializing DynamoDB connection: {str(e)}")
            raise

    def get_cached_account(self, username: str) -> Optional[int]:
        """Get cached account ID for a user."""
        try:
            response = self.table.get_item(
                Key={"cache_key": f"{self.ACCOUNT_CACHE_KEY}_{username}"}
            )
            if "Item" in response:
                item = response["Item"]
                # Check if cache is still valid
                if "ttl" in item and item["ttl"] > int(
                    datetime.now(timezone.utc).timestamp()
                ):
                    return item["account_id"]
            return None
        except ClientError as e:
            logger.error(f"Failed to get cached account: {str(e)}")
            return None

    def cache_account(self, username: str, account_id: int) -> bool:
        """Cache account ID for a user."""
        try:
            expiration = datetime.now(timezone.utc) + timedelta(
                hours=self.CACHE_TTL_HOURS
            )
            self.table.put_item(
                Item={
                    "cache_key": f"{self.ACCOUNT_CACHE_KEY}_{username}",
                    "account_id": account_id,
                    "username": username,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                    "ttl": int(expiration.timestamp()),
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to cache account: {str(e)}")
            return False

    def invalidate_cache(self, username: str) -> bool:
        """Invalidate cached data for a user."""
        try:
            self.table.delete_item(
                Key={"cache_key": f"{self.ACCOUNT_CACHE_KEY}_{username}"}
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to invalidate cache: {str(e)}")
            return False
