import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.config import get_settings
from app.models.user import User

settings = get_settings()


class QuestradeClient:
    """Client for Questrade API integration"""

    def __init__(self, user: User):
        self.user = user
        self.api_server = user.questrade_api_server
        self.access_token = user.questrade_access_token
        self.refresh_token = user.questrade_refresh_token

    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with authorization"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Dict:
        """Make API request with error handling"""
        url = f"{self.api_server}{endpoint}"
        headers = self._get_headers()

        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expired, try to refresh
                self.refresh_access_token()
                # Retry request
                headers = self._get_headers()
                if method == "GET":
                    response = requests.get(url, headers=headers)
                else:
                    response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            raise

    def refresh_access_token(self) -> None:
        """Refresh the access token using refresh token"""
        url = f"{settings.QUESTRADE_LOGIN_URL}/oauth2/token"
        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Update tokens
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.api_server = data["api_server"]

        # Update user in database (caller should commit)
        self.user.questrade_access_token = self.access_token
        self.user.questrade_refresh_token = self.refresh_token
        self.user.questrade_api_server = self.api_server
        expires_in = data.get("expires_in", 1800)
        self.user.questrade_token_expires_at = (
            datetime.utcnow() + timedelta(seconds=expires_in)
        ).isoformat()

    def get_accounts(self) -> List[Dict]:
        """Get list of accounts"""
        data = self._make_request("GET", "/v1/accounts")
        return data.get("accounts", [])

    def get_account_positions(self, account_id: str) -> List[Dict]:
        """Get positions for an account"""
        data = self._make_request("GET", f"/v1/accounts/{account_id}/positions")
        return data.get("positions", [])

    def get_account_balances(self, account_id: str) -> Dict:
        """Get account balances"""
        data = self._make_request("GET", f"/v1/accounts/{account_id}/balances")
        return data.get("combinedBalances", [{}])[0]

    def get_account_activities(
        self, account_id: str, start_date: str, end_date: str
    ) -> List[Dict]:
        """Get account activities (trades, deposits, etc.)"""
        data = self._make_request(
            "GET",
            f"/v1/accounts/{account_id}/activities"
            f"?startTime={start_date}&endTime={end_date}",
        )
        return data.get("activities", [])

    def get_symbol_id(self, symbol: str) -> Optional[int]:
        """Get symbol ID from ticker symbol"""
        # Search for symbol
        data = self._make_request("GET", f"/v1/symbols/search?prefix={symbol}")
        symbols = data.get("symbols", [])

        # Find exact match
        for sym in symbols:
            if sym.get("symbol") == symbol:
                return sym.get("symbolId")
        return None

    def get_quote(self, symbol_id: int) -> Dict:
        """Get real-time quote for a symbol"""
        data = self._make_request("GET", f"/v1/markets/quotes/{symbol_id}")
        quotes = data.get("quotes", [])
        return quotes[0] if quotes else {}

    def place_order(
        self,
        account_id: str,
        symbol_id: int,
        quantity: int,
        order_type: str,
        action: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ) -> Dict:
        """Place a trade order

        Args:
            account_id: Questrade account ID
            symbol_id: Symbol ID from Questrade
            quantity: Number of shares
            order_type: "Market", "Limit", "Stop", "StopLimit"
            action: "Buy" or "Sell"
            price: Limit price (for Limit and StopLimit orders)
            stop_price: Stop price (for Stop and StopLimit orders)
        """
        order_data = {
            "accountNumber": account_id,
            "symbolId": symbol_id,
            "quantity": quantity,
            "icebergQuantity": quantity,
            "orderType": order_type,
            "action": action,
            "timeInForce": "Day",
            "primaryRoute": "AUTO",
            "secondaryRoute": "AUTO",
        }

        if price:
            order_data["limitPrice"] = price
        if stop_price:
            order_data["stopPrice"] = stop_price

        data = self._make_request("POST", f"/v1/accounts/{account_id}/orders", order_data)
        return data.get("orders", [{}])[0]

    def get_order_status(self, account_id: str, order_id: str) -> Dict:
        """Get status of a specific order"""
        data = self._make_request("GET", f"/v1/accounts/{account_id}/orders/{order_id}")
        orders = data.get("orders", [])
        return orders[0] if orders else {}

    def cancel_order(self, account_id: str, order_id: str) -> bool:
        """Cancel an order"""
        try:
            self._make_request("DELETE", f"/v1/accounts/{account_id}/orders/{order_id}")
            return True
        except Exception:
            return False

    def get_executions(self, account_id: str, order_id: str) -> List[Dict]:
        """Get executions for an order"""
        data = self._make_request(
            "GET", f"/v1/accounts/{account_id}/orders/{order_id}/executions"
        )
        return data.get("executions", [])
