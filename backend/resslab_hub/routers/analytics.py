"""
Handle /analytics requests
"""
from fastapi import APIRouter, Query
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest

from resslab_hub.config import settings

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)

MIN_DATE = "2022-07-01"
client = BetaAnalyticsDataClient() if settings.google_application_credentials else None
property_id = settings.analytics_property_id


@router.get("/users", response_model=int)
async def get_users(days: int | None = Query(None)) -> int:
    """
    Get user count
    """
    if not settings.analytics_property_id or not client:
        return -1

    request = RunReportRequest(
        property=f"properties/{property_id}",
        metrics=[Metric(name="totalUsers")],
        date_ranges=[
            DateRange(
                start_date=f"{days}daysAgo" if days is not None else MIN_DATE,
                end_date="today",
            )
        ],
    )
    response = client.run_report(request)
    return int(response.rows[0].metric_values[0].value)
