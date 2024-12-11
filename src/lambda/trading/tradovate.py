"""Tradovate Utility Functions"""

import logging
from typing import Tuple, Optional, Dict, List
from datetime import datetime
import requests
from trading.tradovate_client import TradovateClient

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to DEBUG for development, INFO for production

# Set global variables
DEMO = "https://demo.tradovateapi.com/v1"
LIVE = "https://live.tradovateapi.com/v1"
MD = "https://md.tradovateapi.com/v1"

logger = logging.getLogger()


def get_auth_token(
    username: str, password: str, device_id: str, cid: str, secret: str
) -> Tuple[Optional[str], Optional[datetime]]:
    """
    Get an authentication token from Tradovate.

    Returns:
        Tuple[Optional[str], Optional[datetime]]: a tuple containing the access token and expiration time,
        or (None, None) if authentication fails
    """
    try:
        client = TradovateClient(
            username=username,
            password=password,
            device_id=device_id,
            cid=cid,
            secret=secret,
            demo=True,
        )
        # Get a valid token
        return client.token_manager.get_valid_token(
            get_new_token_func=client.get_new_token
        )
    except Exception as e:
        logger.error(f"Failed to get auth token: {str(e)}")
        return None, None


def get_accounts(
    username: str, password: str, device_id: str, cid: str, secret: str
) -> Optional[int]:
    """
    Get list of accounts from Tradovate API.

    Args:
        access_token (str): The authentication token for API access

    Returns:
        int: The account ID
    """
    try:
        client = TradovateClient(
            username=username,
            password=password,
            device_id=device_id,
            cid=cid,
            secret=secret,
            demo=True,
        )
        # Get account id number
        return client.get_accounts()
    except Exception as e:
        logger.error(f"Failed to get account: {str(e)}")
        return None


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


def get_contract_info(token: str, contract_ids: list[int]) -> List[Dict]:
    """
    Get contract information from Tradovate API.

    Args:
        token (str): The authentication token for API access
        ids (list[int]): The contract IDs to get information for

    Returns:
        dict: JSON response containing contract information
    """
    # Set headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    # Make POST request to get contract info
    response = requests.get(
        f"{DEMO}/contract/items",
        params={"ids": ",".join(str(id) for id in contract_ids)},
        headers=headers,
        timeout=10,
    )

    # Return JSON data from response
    contract_response = response.json()
    logger.debug(f"Contract response: {contract_response}")

    # Create name list to hold contract names
    contract_names_with_ids = []

    # Loop through contracts and get the names
    for contract in contract_response:
        contract_names_with_ids.append(
            {"contractId": contract["id"], "contractName": contract["name"]}
        )

    # Return the contract names
    return contract_names_with_ids


def get_all_positions(token: str) -> List[Dict]:
    """
    Get list of all positions from Tradovate API.

    Args:
        access_token (str): The authentication token for API access

    Returns:
        dict: JSON response containing position information
    """
    try:
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        # Make GET request to get position list
        response = requests.get(f"{DEMO}/position/list", headers=headers, timeout=5)
        # Return JSON data from response
        response.raise_for_status()

        # Get the positions
        positions = response.json()

        # Check if there are any positions
        if not positions:
            logger.info("No positions found")
            return []

        # Create list to hold positions that have a netPos <> 0
        net_positions = []

        # loop through positions
        for position in positions:
            if position["netPos"] != 0:
                net_positions.append(
                    {
                        "contractId": position["contractId"],
                        "accountId": position["accountId"],
                    }
                )

        # Return all positions
        return net_positions

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting position: {str(e)}")
        return []


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

    # Create request body with integer conversion
    body = {
        "accountId": int(account_id),
        "contractId": int(contract_id),
        "admin": False,
    }

    # Log the request details
    logger.info(f"Attempting to liquidate position for contract {contract_id}")
    logger.debug(f"Liquidation request body: {body}")

    # Make POST request to liquidate position
    response = requests.post(
        f"{DEMO}/order/liquidateposition", headers=headers, timeout=5, json=body
    )

    # Log the complete response
    logger.debug(f"Liquidation response status: {response.status_code}")
    logger.debug(f"Liquidation response body: {response.text}")

    result = response.json()

    # Validate we got an order ID back
    if "orderId" in result:
        logger.info(f"Successfully liquidated position. Order ID: {result['orderId']}")
    else:
        logger.error(f"Unexpected liquidation response format: {result}")

    return result


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
        "accountId": int(account_id),
        "action": "Buy",
        "symbol": instrument,
        "orderQty": int(quantity),
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
        "accountId": int(account_id),
        "action": "Sell",
        "symbol": instrument,
        "orderQty": int(quantity),
        "orderType": "Market",
        "isAutomated": True,
    }
    # Make POST request to place sell order
    response = requests.post(
        f"{DEMO}/order/placeorder", headers=headers, timeout=5, json=body
    )
    # Return JSON data from response
    return response.json()
