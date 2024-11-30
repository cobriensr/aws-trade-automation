"""Tradovate Utility Functions"""

import os
from pathlib import Path
from typing import Tuple, Callable, Any, Optional
from datetime import datetime
import time
from dotenv import load_dotenv
import requests

# from .tradovate_token import TokenManager

# live.tradovateapi.com for Live only functionality.
# demo.tradovateapi.com for simulation engine.
# md.tradovateapi.com and for a market data feed.

# Use relative path navigation
load_dotenv(Path(__file__).parents[3] / ".env")

# Set global variables
DEMO = "https://demo.tradovateapi.com/v1"
LIVE = "https://live.tradovateapi.com/v1"
MD = "https://md.tradovateapi.com/v1"
username = os.getenv("TRADOVATE_USERNAME")
password = os.getenv("TRADOVATE_PASSWORD")
device_id = os.getenv("TRADOVATE_DEVICE_ID")
cid = os.getenv("TRADOVATE_CID")
secret = os.getenv("TRADOVATE_SECRET")


def retry_with_ticket(api_call: Callable) -> Any:
    """
    Decorator to handle API responses with p-ticket structure and retry logic.
    Will retry after p-time seconds if p-captcha is False.
    """

    def wrapper(*args, **kwargs) -> Tuple[Optional[str], Optional[datetime]]:
        while True:
            response = api_call(*args, **kwargs)
            json_data = response.json()

            # Check if response has ticket structure
            if isinstance(json_data, dict) and "p-ticket" in json_data:
                p_time = json_data.get("p-time", 0)
                p_captcha = json_data.get("p-captcha", False)

                # If p-captcha is True, don't retry and return None values
                if p_captcha:
                    return None, None

                # If p-captcha is False, wait p-time seconds and retry
                print(f"Waiting {p_time} seconds before retry...")
                time.sleep(p_time)
                continue

            # If no p-ticket, return the response as is
            return response

    return wrapper


@retry_with_ticket
def get_auth_token() -> Tuple[Optional[str], Optional[datetime]]:
    """
    Get an authentication token from Tradovate.

    Returns:
        Tuple[Optional[str], Optional[datetime]]: a tuple containing the access token and expiration time,
        or (None, None) if authentication fails
    """
    body = {
        "name": username,
        "password": password,
        "appId": "Automation",
        "appVersion": "0.0.1",
        "deviceId": device_id,
        "cid": cid,
        "sec": secret,
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    response = requests.post(
        f"{LIVE}/auth/accesstokenrequest", headers=headers, timeout=5, json=body
    )

    json_data = response.json()
    try:
        access_token = json_data["accessToken"]
        expiration_time = json_data["expirationTime"]
        expiration_datetime = datetime.fromisoformat(
            expiration_time.replace("Z", "+00:00")
        )
        return access_token, expiration_datetime
    except KeyError as e:
        raise KeyError(f"Unexpected response structure. Missing key: {e}") from e


def get_accounts(access_token: str) -> dict:
    """
    Get list of accounts from Tradovate API.

    Args:
        access_token (str): The authentication token for API access

    Returns:
        dict: JSON response containing account information
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.get(f"{LIVE}/account/list", headers=headers, timeout=5)

    return response.json()


# TODO - Move this into the lambda handler function
def main():
    try:
        access_token, expiration_time = get_auth_token()
        if access_token is None:
            print(
                "Failed to get access token - captcha required or authentication failed"
            )
        else:
            print(f"Successfully obtained access token. Expires at: {expiration_time}")
    except Exception as e:
        print(f"Error getting auth token: {e}")


if __name__ == "__main__":
    main()
