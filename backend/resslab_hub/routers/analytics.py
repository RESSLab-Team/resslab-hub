import logging
from logging import INFO, basicConfig

import requests
from fastapi import APIRouter, Query
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


def get_access_token():
    """
    Generate an OAuth2 token to authenticate API requests.
    """
    try:
        # Load the service account credentials
        credentials = service_account.Credentials.from_service_account_file(
            settings.google_application_credentials,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        # Refresh to get a new access token
        credentials.refresh(Request())
        return credentials.token
    except Exception as exc:
        logging.error(exc)
        return None


@router.get("/users", response_model=int)
async def get_users(days: int | None = Query(None)) -> int:
    """
    Get user count using Google Analytics Data API with requests.
    """
    if not settings.analytics_property_id:
        return -1

    # Define the request payload
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

    # Set up the authorization headers
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
    }

    try:
        # Make the request to the Google Analytics Data API

        response = requests.post(
            (
                f"https://analyticsdata.googleapis.com/v1beta/properties/"
                f"{property_id}:runReport"
            ),
            json=request_payload,
            headers=headers,
        )
        # Handle errors in the response
        if response.status_code != 200:
            return -1

        # Parse the JSON response
        data = response.json()
        return int(data["rows"][0]["metricValues"][0]["value"])
    except Exception as exc:
        if exc is not None:
            logging.error("failed to retrieve google analytics because %r", exc)
        return -1
