"""Tradovate Utility Functions"""

import logging
from typing import Tuple, Optional, Dict
from datetime import datetime
import requests

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production


# Set global variables
DEMO = "https://demo.tradovateapi.com/v1"
LIVE = "https://live.tradovateapi.com/v1"
MD = "https://md.tradovateapi.com/v1"


def get_auth_token(
    username: str, password: str, device_id: str, cid: str, secret: str
) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Get an authentication token from Tradovate.

    Returns:
        Tuple[Optional[str], Optional[datetime]]: a tuple containing the access token and expiration time,
        or (None, None) if authentication fails
    """
    # Create request body
    body = {
        "name": username,
        "password": password,
        "appId": "Automation",
        "appVersion": "0.0.1",
        "deviceId": device_id,
        "cid": cid,
        "sec": secret,
    }
    # Set headers
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    # Make POST request to get access token
    response = requests.post(
        f"{DEMO}/auth/accesstokenrequest", headers=headers, timeout=5, json=body
    )
    # Get JSON data from response
    json_data = response.json()
    # Check if response has expected structure
    try:
        access_token = json_data["accessToken"]
        expiration_time = json_data["expirationTime"]
        expiration_datetime = datetime.fromisoformat(
            expiration_time.replace("Z", "+00:00")
        )
        return access_token, expiration_datetime
    except KeyError as e:
        raise KeyError(f"Unexpected response structure. Missing key: {e}") from e


def get_accounts(access_token: str) -> int:
    """
    Get list of accounts from Tradovate API.

    Args:
        access_token (str): The authentication token for API access

    Returns:
        dict: JSON response containing account information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    # Make GET request to get account list
    response = requests.get(f"{DEMO}/account/list", headers=headers, timeout=5)
    # Return JSON data from response
    data = response.json()
    account_id = data[0]["id"]
    return account_id


def get_cash_balance_snapshot(access_token: str, account_id: str) -> Dict:
    """
    Get cash balance snapshot from Tradovate API.

    Args:
        access_token (str): The authentication token for API access
        account_id (str): The account ID to get the cash balance for

    Returns:
        dict: JSON response containing cash balance snapshot information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Set body
    body = {
        "accountId": int(account_id),
    }

    try:
        # Make POST request to get cash balance snapshot
        response = requests.post(
            f"{DEMO}/cashBalance/getCashBalanceSnapshot",
            headers=headers,
            json=body,
            timeout=5,
        )
        # check for HTTP error
        response.raise_for_status()
        # Return JSON data from response
        data = response.json()
        # Replace "NaN" values with 0
        for key, value in data.items():
            if value == "NaN":
                data[key] = 0.0
        # Return the data
        return data

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {e}, Response: {response.text}")
        if response.status_code == 404:
            return {"error": "Endpoint not found. Please verify the API endpoint path."}
        return {"error": f"HTTP Error: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error(f"Request Error: {e}")
        return {"error": f"Request failed: {str(e)}"}
    except ValueError as e:
        logger.error(f"JSON Decode Error: {e}")
        return {"error": "Could not parse response from server"}


def get_position(token: str, instrument: str) -> Tuple[int, int, int]:
    """
    Get list of all positions from Tradovate API.

    Args:
        access_token (str): The authentication token for API access

    Returns:
        dict: JSON response containing position information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    # Make GET request to get position list
    response = requests.get(
        f"{DEMO}/position/list?name={instrument}", headers=headers, timeout=5
    )
    # Return JSON data from response
    data = response.json()
    if len(data) > 0:
        # Extract account ID, contract ID, and net position
        account_id = data["accountId"]
        contract_id = data["contractId"]
        net_position = data["netPos"]
        # Return account ID, contract ID, and net position
        return account_id, contract_id, net_position
    return None, None, None


def liquidate_position(contract_id: str, account_id: str, token: str) -> Dict:
    """
    Liquidate a position for a given contract and account.

    Args:
        contract_id (str): The contract ID of the position to liquidate
        account_id (str): The account ID of the position to liquidate
        token (str): The authentication token for API access

    Returns:
        dict: JSON response containing liquidation information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    # Create request body
    body = {"accountId": account_id, "contractId": contract_id, "admin": False}
    # Make POST request to liquidate position
    response = requests.post(
        f"{DEMO}/order/liquidateposition", headers=headers, timeout=5, json=body
    )
    # Return JSON data from response
    return response.json()


def place_buy_order(
    username: str, instrument: str, account_id: str, quantity: int, token: str
) -> Dict:
    """
    Place a buy order for a given contract and account.

    Args:
        instrument (str): The instrument to place the order for
        account_id (str): The account ID of the order
        quantity (int): The quantity of the order
        token (str): The authentication token for API access

    Returns:
        dict: JSON response containing order information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    # Create request body
    body = {
        "accountSpec": username,
        "accountId": account_id,
        "action": "Buy",
        "symbol": instrument,
        "orderQty": quantity,
        "orderType": "Market",
        "isAutomated": True,
    }
    # Make POST request to place buy order
    response = requests.post(
        f"{DEMO}/order/placeorder", headers=headers, timeout=5, json=body
    )
    # Return JSON data from response
    return response.json()


def place_sell_order(
    username: str, instrument: str, account_id: str, quantity: int, token: str
) -> Dict:
    """
    Place a sell order for a given contract and account.

    Args:
        instrument (str): The instrument to place the order for
        account_id (str): The account ID of the order
        quantity (int): The quantity of the order
        token (str): The authentication token for API access

    Returns:
        dict: JSON response containing order information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    # Create request body
    body = {
        "accountSpec": username,
        "accountId": account_id,
        "action": "Sell",
        "symbol": instrument,
        "orderQty": quantity,
        "orderType": "Market",
        "isAutomated": True,
    }
    # Make POST request to place sell order
    response = requests.post(
        f"{DEMO}/order/placeorder", headers=headers, timeout=5, json=body
    )
    # Return JSON data from response
    return response.json()
