"""Tradovate token management with DynamoDB for webhook-based Lambda."""

from datetime import datetime, timezone
import logging
from typing import Optional, Tuple, Dict
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()


class TokenManager:
    """Manages Tradovate authentication tokens using DynamoDB."""

    def __init__(self, table_name: str = "tradovate-tokens"):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)
        self.TOKEN_KEY = "CURRENT_TOKEN"
        # Time before expiration to get new token (15 minutes)
        self.SAFE_THRESHOLD_MINUTES = 15
        # Maximum age of token before forcing refresh (75 minutes)
        self.MAX_TOKEN_AGE_MINUTES = 75

    def _get_token_record(self) -> Optional[Dict]:
        """Get the current token record from DynamoDB."""
        try:
            response = self.table.get_item(Key={"id": self.TOKEN_KEY})
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get token from DynamoDB: {str(e)}")
            return None

    def _save_token(self, access_token: str, expiration_time: datetime) -> bool:
        """Save token to DynamoDB with expiration time."""
        try:
            now = datetime.now(timezone.utc)
            self.table.put_item(
                Item={
                    "id": self.TOKEN_KEY,
                    "access_token": access_token,
                    "expiration_time": expiration_time.isoformat(),
                    "created_at": now.isoformat(),
                    "ttl": int(expiration_time.timestamp()),
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Failed to save token to DynamoDB: {str(e)}")
            return False

    def _should_get_new_token(self, token_record: Dict) -> bool:
        """
        Determine if we should get a new token based on age and expiration.
        Returns True if:
        - No token exists
        - Token is expired or will expire within SAFE_THRESHOLD_MINUTES
        - Token is older than MAX_TOKEN_AGE_MINUTES
        """
        if not token_record:
            logger.info("No token record found")
            return True

        try:
            now = datetime.now(timezone.utc)
            expiration_time = datetime.fromisoformat(token_record["expiration_time"])
            created_at = datetime.fromisoformat(token_record["created_at"])

            # Check if token is expired or will expire soon
            time_until_expiry = expiration_time - now
            minutes_until_expiry = time_until_expiry.total_seconds() / 60

            # Check token age
            token_age = (now - created_at).total_seconds() / 60

            if minutes_until_expiry <= self.SAFE_THRESHOLD_MINUTES:
                logger.info(
                    f"Token will expire soon (expires in {minutes_until_expiry:.1f} minutes)"
                )
                return True

            if token_age >= self.MAX_TOKEN_AGE_MINUTES:
                logger.info(f"Token is too old (age: {token_age:.1f} minutes)")
                return True

            logger.info(
                f"Token is valid (expires in {minutes_until_expiry:.1f} minutes, age: {token_age:.1f} minutes)"
            )
            return False

        except (KeyError, ValueError) as e:
            logger.error(f"Error checking token status: {str(e)}")
            return True

    def get_valid_token(
        self, get_new_token_func
    ) -> Tuple[Optional[str], Optional[datetime]]:
        """
        Get a valid token, either from cache or by requesting a new one.

        Args:
            get_new_token_func: Function to call to get a new token

        Returns:
            Tuple of (access_token, expiration_time) or (None, None) if failed
        """
        try:
            # Get current token record
            token_record = self._get_token_record()

            # Check if we need a new token
            if self._should_get_new_token(token_record):
                logger.info("Getting new token...")
                new_token, new_expiration = get_new_token_func()
                if new_token:
                    logger.info("Successfully obtained new token")
                    self._save_token(new_token, new_expiration)
                    return new_token, new_expiration
                logger.error("Failed to obtain new token")
                return None, None

            # Return existing valid token
            return token_record["access_token"], datetime.fromisoformat(
                token_record["expiration_time"]
            )

        except Exception as e:
            logger.error(f"Error in get_valid_token: {str(e)}")
            return None, None
