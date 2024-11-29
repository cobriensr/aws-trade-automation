"""Token management utilities for Tradovate API"""

from datetime import datetime
from typing import Optional, Tuple
import boto3

class TokenManager:
    """
    Manages Tradovate API token and expiry in AWS Parameter Store
    """
    def __init__(self):
        self.ssm = boto3.client('ssm')
        self.token_parameter = "/tradovate/token"
        self.expiry_parameter = "/tradovate/token_expiry"
        
    def save_token(self, token: str, expiry: datetime) -> None:
        """Save token and expiry to Parameter Store"""
        try:
            # Save token
            self.ssm.put_parameter(
                Name=self.token_parameter,
                Value=token,
                Type='SecureString',
                Overwrite=True
            )
            
            # Save expiry
            self.ssm.put_parameter(
                Name=self.expiry_parameter,
                Value=expiry.isoformat(),
                Type='String',
                Overwrite=True
            )
        except Exception as e:
            print(f"Error saving token to Parameter Store: {e}")
            raise
            
    def get_token(self) -> Tuple[Optional[str], Optional[datetime]]:
        """
        Get token and expiry from Parameter Store
        Returns tuple of (token, expiry) or (None, None) if not found
        """
        try:
            # Get token
            token_response = self.ssm.get_parameter(
                Name=self.token_parameter,
                WithDecryption=True
            )
            
            # Get expiry
            expiry_response = self.ssm.get_parameter(
                Name=self.expiry_parameter
            )
            
            token = token_response['Parameter']['Value']
            expiry = datetime.fromisoformat(expiry_response['Parameter']['Value'])
            
            return token, expiry
            
        except self.ssm.exceptions.ParameterNotFound:
            return None, None
        except Exception as e:
            print(f"Error retrieving token from Parameter Store: {e}")
            return None, None
            
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not near expiration"""
        token, expiry = self.get_token()
        if token and expiry:
            # Check if token is valid and not within 15 minutes of expiring
            time_until_expiry = (expiry - datetime.now()).total_seconds()
            return time_until_expiry > 900  # 15 minutes in seconds
        return False