"""OANDA Utility Functions"""

from typing import Dict
import requests

# Set global variables
PRACTICE = "https://api-fxpractice.oanda.com"
LIVE = "https://api-fxtrade.oanda.com"

FOREX_UNITS = {
    "STANDARD_LOT": 100000,  # Standard lot is 100,000 units
    "MINI_LOT": 10000,  # Mini lot is 10,000 units
    "MICRO_LOT": 1000,  # Micro lot is 1,000 units
    "NANO_LOT": 100,  # Nano lot is 100 units
}

LOT_SIZES = {
    1.0: "STANDARD_LOT",  # 1.0 lot = 100,000 units
    0.1: "MINI_LOT",  # 0.1 lot = 10,000 units
    0.01: "MICRO_LOT",  # 0.01 lot = 1,000 units
    0.001: "NANO_LOT",  # 0.001 lot = 100 units
}

SYMBOL_MAP = {
    "EURUSD": "EUR_USD",
    "USDJPY": "USD_JPY",
    "GBPUSD": "GBP_USD",
    "USDCHF": "USD_CHF",
    "USDCAD": "USD_CAD",
    "AUDUSD": "AUD_USD",
    "NZDUSD": "NZD_USD",
    "EURJPY": "EUR_JPY",
    "GBPJPY": "GBP_JPY",
    "EURGBP": "EUR_GBP",
    "AUDJPY": "AUD_JPY",
    "EURAUD": "EUR_AUD",
}


class OandaAuthError(Exception):
    """Raised when there are authorization issues with OANDA API"""


def check_position_exists(account_id: str, instrument: str, access_token: str) -> bool:
    """
    Check if a position exists for a given instrument

    Args:
        account_id (str): The OANDA account ID
        instrument (str): The instrument to check (e.g. "EURUSD")
        access_token (str): The authentication token

    Returns:
        bool: True if position exists, False otherwise
    """

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Send the request to the OANDA API
    response = requests.get(
        f"{PRACTICE}/v3/accounts/{account_id}/openPositions", headers=headers, timeout=5
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")

    # Convert response to JSON
    positions = response.json()

    # Map the instrument to the OANDA symbol
    oanda_instrument = SYMBOL_MAP[instrument]

    # Check if instrument exists in any position
    for position in positions.get("positions", []):
        if position["instrument"] == oanda_instrument:
            return True
    # If no position found, return False
    return False


def close_long_position(account_id: str, instrument: str, access_token: str) -> Dict:
    """
    Close an existing long position for an instrument

    Args:
        account_id (str): The OANDA account ID
        instrument (str): The instrument to close (e.g. "EUR_USD")
        access_token (str): The authentication token

    Returns:
        dict: JSON response from the API
    """

    # Map the instrument to the OANDA symbol
    trade_symbol = SYMBOL_MAP[instrument]

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Set the body of the request
    body = {"longUnits": "ALL"}

    # Send the request to the OANDA API
    response = requests.put(
        f"{PRACTICE}/v3/accounts/{account_id}/positions/{trade_symbol}/close",
        headers=headers,
        json=body,
        timeout=5,
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 200:
        return {"success": True, "message": "Position closeout successfully processed"}
    if response.status_code == 400:
        raise ValueError("The parameters provided for position closeout are invalid")
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")
    if response.status_code == 404:
        raise LookupError("The account or position specified does not exist")
    raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")


def close_short_position(account_id: str, instrument: str, access_token: str) -> Dict:
    """
    Close an existing long position for an instrument

    Args:
        account_id (str): The OANDA account ID
        instrument (str): The instrument to close (e.g. "EUR_USD")
        access_token (str): The authentication token

    Returns:
        dict: JSON response from the API
    """

    # Map the instrument to the OANDA symbol
    trade_symbol = SYMBOL_MAP[instrument]

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    # Set the body of the request
    body = {"shortUnits": "ALL"}

    # Send the request to the OANDA API
    response = requests.put(
        f"{PRACTICE}/v3/accounts/{account_id}/positions/{trade_symbol}/close",
        headers=headers,
        json=body,
        timeout=5,
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 200:
        return {"success": True, "message": "Position closeout successfully processed"}
    if response.status_code == 400:
        raise ValueError("The parameters provided for position closeout are invalid")
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")
    if response.status_code == 404:
        raise LookupError("The account or position specified does not exist")
    raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")


def create_long_market_order(
    account_id: str, instrument: str, access_token: str
) -> Dict:
    """
    Create a market order

    Args:
        account_id (str): The OANDA account ID
        instrument (str): The trading instrument (e.g. "EUR_USD")
        access_token (str): The authentication token

    Returns:
        dict: JSON response from the API
    """

    # Set the trade units and symbol based on the instrument
    trade_units = str(FOREX_UNITS["STANDARD_LOT"])
    trade_symbol = SYMBOL_MAP[instrument]

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Set the body of the request
    body = {
        "order": {
            "units": trade_units,
            "instrument": trade_symbol,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
        }
    }

    # Send the request to the OANDA API
    response = requests.post(
        f"{PRACTICE}/v3/accounts/{account_id}/orders",
        headers=headers,
        json=body,
        timeout=5,
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 201:
        return {
            "success": True,
            "message": "Order was created as specified",
            "order_details": response.json(),
        }
    if response.status_code == 400:
        raise ValueError("The order specification was invalid")
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")
    if response.status_code == 404:
        raise LookupError("The Order or Account specified does not exist")
    raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")


def create_short_market_order(
    account_id: str, instrument: str, access_token: str
) -> Dict:
    """
    Create a market order

    Args:
        account_id (str): The OANDA account ID
        instrument (str): The trading instrument (e.g. "EUR_USD")
        access_token (str): The authentication token

    Returns:
        dict: JSON response from the API
    """

    # Set the trade units and symbol based on the instrument
    trade_units = str(-FOREX_UNITS["STANDARD_LOT"])
    trade_symbol = SYMBOL_MAP[instrument]

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Set the body of the request
    body = {
        "order": {
            "units": trade_units,
            "instrument": trade_symbol,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
        }
    }

    # Send the request to the OANDA API
    response = requests.post(
        f"{PRACTICE}/v3/accounts/{account_id}/orders",
        headers=headers,
        json=body,
        timeout=5,
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 201:
        return {
            "success": True,
            "message": "Order was created as specified",
            "order_details": response.json(),
        }
    if response.status_code == 400:
        raise ValueError("The order specification was invalid")
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")
    if response.status_code == 404:
        raise LookupError("The Order or Account specified does not exist")
    raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")


def check_account_status(account_id: str, access_token: str) -> Dict:
    """
    Check the status of an OANDA account

    Args:
        account_id (str): The OANDA account ID
        access_token (str): The authentication token

    Returns:
        dict: JSON response from the API
    """

    # Set the headers for the API request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # Send the request to the OANDA API
    response = requests.get(
        f"{PRACTICE}/v3/accounts/{account_id}/summary",
        headers=headers,
        timeout=5,
    )

    # Parse error message if present
    error_message = response.json().get("errorMessage", "") if response.content else ""

    # Check the response status code and raise an error if necessary
    if response.status_code == 200:
        data = response.json()
        return {
            "account_id": data["account"]["id"],
            "balance": data["account"]["balance"],
            "unrealized_pl": data["account"]["unrealizedPL"],
            "realized_pl": data["account"]["pl"],
            "margin_used": data["account"]["marginUsed"],
            "margin_available": data["account"]["marginAvailable"],
            "position_value": data["account"]["positionValue"],
            "last_transaction": data["lastTransactionID"],
        }
    if response.status_code == 401:
        raise OandaAuthError(f"Authentication failed: {error_message}")
    if response.status_code == 404:
        raise LookupError("The account specified does not exist")
    raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")
