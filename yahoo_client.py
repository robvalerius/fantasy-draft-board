"""Yahoo Fantasy Sports API client with OAuth2 token management."""

import base64
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"

TOKEN_FILE = Path(__file__).parent / "tokens.json"

CLIENT_ID = os.getenv("YAHOO_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("YAHOO_REDIRECT_URI", "")
LEAGUE_ID = os.getenv("LEAGUE_ID", "204761")


def _basic_auth_header() -> str:
    raw = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def build_authorize_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "language": "en-us",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _save_tokens(payload: dict) -> dict:
    payload["expires_at"] = time.time() + int(payload.get("expires_in", 3600)) - 60
    TOKEN_FILE.write_text(json.dumps(payload, indent=2))
    return payload


def exchange_code(code: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return _save_tokens(resp.json())


def _refresh(refresh_token: str) -> dict:
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "redirect_uri": REDIRECT_URI,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return _save_tokens(resp.json())


def get_access_token() -> str:
    if not TOKEN_FILE.exists():
        raise RuntimeError("No tokens.json found. Run: python auth.py")
    tokens = json.loads(TOKEN_FILE.read_text())
    if time.time() >= tokens.get("expires_at", 0):
        tokens = _refresh(tokens["refresh_token"])
    return tokens["access_token"]


def api_get(path: str) -> dict:
    """GET a Fantasy API resource. Path is relative, e.g. 'league/nfl.l.204761'."""
    url = f"{API_BASE}/{path.lstrip('/')}"
    joiner = "&" if "?" in url else "?"
    resp = requests.get(
        f"{url}{joiner}format=json",
        headers={"Authorization": f"Bearer {get_access_token()}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def current_nfl_game_key() -> str:
    data = api_get("game/nfl")
    return data["fantasy_content"]["game"][0]["game_key"]


def league_key() -> str:
    return f"{current_nfl_game_key()}.l.{LEAGUE_ID}"
