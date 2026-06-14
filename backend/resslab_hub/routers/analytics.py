import logging
import time
from logging import INFO, basicConfig
from threading import Lock

import requests
from fastapi import APIRouter, Query
from fastapi.concurrency import run_in_threadpool
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from resslab_hub.config import settings

basicConfig(level=INFO)
router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)

MIN_DATE = "2022-07-01"
property_id = settings.analytics_property_id
GA_TIMEOUT = 10  # seconds, so a slow Google call can't hang a worker indefinitely

# Cache the OAuth token to avoid re-minting it (a blocking network call) on
# every request. Google access tokens are valid ~1h; refresh well before then.
_TOKEN_TTL = 3000  # ~50 min
_token_cache: dict = {"token": None, "expiry": 0.0}
_token_lock = Lock()

# Cache the (slow-changing) user-count result per `days` window for a short
# time so the home page's repeated calls don't each hit Google Analytics.
_RESULT_TTL = 300  # 5 min
_result_cache: dict = {}
_result_lock = Lock()


def get_access_token():
    """
    Generate (and cache) an OAuth2 token to authenticate API requests.
    """
    with _token_lock:
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expiry"]:
            return _token_cache["token"]
        try:
            # Load the service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                settings.google_application_credentials,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            # Refresh to get a new access token
            credentials.refresh(Request())
            _token_cache["token"] = credentials.token
            _token_cache["expiry"] = now + _TOKEN_TTL
            return credentials.token
        except Exception as exc:
            logging.error(exc)
            return None


def _fetch_user_count(days: int | None) -> int:
    """
    Blocking call to the Google Analytics Data API. Runs in a threadpool so it
    does not block the worker's event loop.
    """
    token = get_access_token()
    if token is None:
        return -1

    request_payload = {
        "property": f"{property_id}",
        "metrics": [{"name": "totalUsers"}],
        "dateRanges": [
            {
                "startDate": f"{days}daysAgo" if days is not None else MIN_DATE,
                "endDate": "today",
            }
        ],
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            (
                f"https://analyticsdata.googleapis.com/v1beta/properties/"
                f"{property_id}:runReport"
            ),
            json=request_payload,
            headers=headers,
            timeout=GA_TIMEOUT,
        )
        if response.status_code != 200:
            return -1
        data = response.json()
        return int(data["rows"][0]["metricValues"][0]["value"])
    except Exception as exc:
        if exc is not None:
            logging.error("failed to retrieve google analytics because %r", exc)
        return -1


@router.get("/users", response_model=int)
async def get_users(days: int | None = Query(None)) -> int:
    """
    Get user count using Google Analytics Data API.
    """
    if not settings.analytics_property_id:
        return -1

    now = time.time()
    with _result_lock:
        cached = _result_cache.get(days)
        if cached and now < cached[1]:
            return cached[0]

    # Offload the blocking auth + HTTP calls so the event loop stays free.
    count = await run_in_threadpool(_fetch_user_count, days)

    if count != -1:
        with _result_lock:
            _result_cache[days] = (count, now + _RESULT_TTL)
    return count
