"""Tradovate API client with webhook-optimized token management."""

from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
import requests
from trading.token_manager import TokenManager

logger = logging.getLogger()


class TradovateClient:
    """Client for Tradovate API with token management."""

    def __init__(
        self,
        username: str,
        password: str,
        device_id: str,
        cid: str,
        secret: str,
        demo: bool = True,
    ):
        self.username = username
        self.password = password
        self.device_id = device_id
        self.cid = cid
        self.secret = secret
        self.base_url = (
            "https://demo.tradovateapi.com/v1"
            if demo
            else "https://live.tradovateapi.com/v1"
        )
        self.token_manager = TokenManager()

    def get_new_token(self) -> Tuple[Optional[str], Optional[datetime]]:
        """Get new auth token from Tradovate."""
        try:
            body = {
                "name": self.username,
                "password": self.password,
                "appId": "Automation",
                "appVersion": "0.0.1",
                "deviceId": self.device_id,
                "cid": int(self.cid),
                "sec": self.secret,
            }
            headers = {"Content-Type": "application/json"}

            logger.info("Requesting new access token from Tradovate")
            response = requests.post(
                f"{self.base_url}/auth/accesstokenrequest",
                headers=headers,
                json=body,
                timeout=5,
            )
            response.raise_for_status()

            data = response.json()
            access_token = data["accessToken"]
            expiration_time = datetime.fromisoformat(
                data["expirationTime"].replace("Z", "+00:00")
            )

            logger.info(f"Successfully obtained new token, expires: {expiration_time}")
            return access_token, expiration_time

        except Exception as e:
            logger.error(f"Failed to get new token: {str(e)}")
            return None, None

    def get_valid_token(self) -> Optional[str]:
        """Get a valid token using the token manager."""
        token, _ = self.token_manager.get_valid_token(
            get_new_token_func=self.get_new_token
        )
        return token

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """Make an authenticated request to the Tradovate API."""
        token = self.get_valid_token()
        if not token:
            raise ValueError("Failed to obtain valid token")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=5,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise

    # API Methods
    def get_accounts(self) -> int:
        """Get the default account ID."""
        response = self._make_request("GET", "account/list")
        return response[0]["id"]

    def get_positions(self) -> list:
        """Get all positions with non-zero netPos."""
        positions = self._make_request("GET", "position/list")
        return [
            {"contractId": pos["contractId"], "accountId": pos["accountId"]}
            for pos in positions
            if pos["netPos"] != 0
        ]

    def get_contract_info(self, contract_ids: list[int]) -> list:
        """Get contract information for given IDs."""
        response = self._make_request(
            "GET",
            "contract/items",
            params={"ids": ",".join(str(id) for id in contract_ids)},
        )
        return [
            {"contractId": contract["id"], "contractName": contract["name"]}
            for contract in response
        ]

    def liquidate_position(self, contract_id: int, account_id: int) -> Dict:
        """Liquidate a position."""
        return self._make_request(
            "POST",
            "order/liquidateposition",
            data={"accountId": account_id, "contractId": contract_id, "admin": False},
        )

    def place_order(
        self, account_id: int, symbol: str, action: str, quantity: int
    ) -> Dict:
        """Place a market order."""
        return self._make_request(
            "POST",
            "order/placeorder",
            data={
                "accountSpec": self.username,
                "accountId": account_id,
                "action": action,
                "symbol": symbol,
                "orderQty": quantity,
                "orderType": "Market",
                "isAutomated": True,
            },
        )
