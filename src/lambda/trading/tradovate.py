"""Tradovate Utility Functions"""

from typing import Tuple, Optional, Dict
from datetime import datetime, timedelta
import requests
import databento as db

# Set global variables
DEMO = "https://demo.tradovateapi.com/v1"
LIVE = "https://live.tradovateapi.com/v1"
MD = "https://md.tradovateapi.com/v1"


def get_historical_data_dict(api_key: str) -> Dict:
    # Retrieve yesterday's and today's date in the format required by the API
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    data_start = yesterday.strftime("%Y-%m-%d")
    data_end = today.strftime("%Y-%m-%d")

    # Create a client instance
    db_client = db.Historical(api_key)

    # Mapping of symbol names to the ones used in the API
    symbol_mapping = {
        "MES.n.0": "MES1!",
        "MNQ.n.0": "MNQ1!",
        "YM.n.0": "YM1!",
        "RTY.n.0": "RTY1!",
        "NG.n.0": "NG1!",
        "GC.n.0": "GC1!",
        "CL.n.0": "CL1!",
    }
    # Get historical data for the specified symbols
    df = db_client.timeseries.get_range(
        dataset="GLBX.MDP3",
        schema="definition",
        stype_in="continuous",
        symbols=list(symbol_mapping.keys()),
        start=data_start,
        end=data_end,
    ).to_df()
    # Extract the date and symbol columns
    df["date"] = df.index.date
    # Pivot the data to have symbols as columns
    pivoted = df.pivot(index="date", columns="symbol", values="raw_symbol")

    # Get just the latest row and convert to simple dictionary
    latest_data = pivoted.iloc[-1].to_dict()
    # Map the symbol names to the ones used in the API
    return {symbol_mapping[k]: v for k, v in latest_data.items()}


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


def liquidate_position(contract_id: str, account_id: str, token: str) -> dict:
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
) -> dict:
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
) -> dict:
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
