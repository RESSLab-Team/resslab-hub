"""
Handle /verification requests (#253): the rows still waiting for a curator to
check them, and the button that opens their verification pull request.

The list comes from the database, so it is what the site shows, with the
pending pull requests read off GitHub next to it. A verification merged on
GitHub stays in the list until the next upload; the button then answers 409
("already verified"), since it reads the data repository, not the database.
Curators only, both ways. See ``contributions/verification.py``.
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from resslab_hub.auth import roles
from resslab_hub.auth.deps import require_contributions_enabled, require_role
from resslab_hub.contributions.github import DataRepoClient, configured
from resslab_hub.contributions.projection import SubmissionError
from resslab_hub.contributions.verification import (
    open_verification,
    pending_verifications,
)
from resslab_hub.data.curation_status import UNVERIFIED
from resslab_hub.data.uploader import Type
from resslab_hub.models.database.auth import User
from resslab_hub.models.database.brace import Brace
from resslab_hub.models.database.column import ColumnEntity
from resslab_hub.models.database.connection import Connection
from resslab_hub.models.database.ductile_fracture import DuctileFracture
from resslab_hub.models.database.eccentric_braced_frame import EccentricBracedFrame
from resslab_hub.models.database.hss_column import HSSColumn
from resslab_hub.models.database.material import Material
from resslab_hub.models.database.residual_stress import ResidualStress
from resslab_hub.models.database.tensile_coupon import TensileCoupon
from resslab_hub.models.verification import (
    VerificationGroup,
    VerificationListResponse,
    VerificationPull,
    VerificationRequest,
    VerificationResponse,
)
from resslab_hub.routers.contributions import _contributor
from resslab_hub.routers.curation import invalidate_open_pulls, open_pulls
from resslab_hub.utils.database import get_session
from resslab_hub.utils.rate_limit import limiter

# Router-level, so it runs before the sign-in check of each route.
router = APIRouter(dependencies=[Depends(require_contributions_enabled)])

#: The databases a contribution can go to, and so the ones with a status.
VERIFIABLE: Dict[Type, Any] = {
    Type.ALL_BRACE: Brace,
    Type.ALL_COLUMN: ColumnEntity,
    Type.ALL_CONNECTION: Connection,
    Type.ALL_MATERIAL: Material,
    Type.ALL_TENSILE_COUPON: TensileCoupon,
    Type.ALL_DUCTILE_FRACTURE: DuctileFracture,
    Type.ALL_RESIDUAL_STRESS: ResidualStress,
    Type.ALL_HSS_COLUMN: HSSColumn,
    Type.ALL_ECCENTRIC_BRACED_FRAME: EccentricBracedFrame,
}


def group_unverified(
    rows: List[Tuple[Type, str, Optional[str]]],
    pending: Dict[Tuple[Type, str], dict],
) -> List[VerificationGroup]:
    """(type, id, reference) rows -> one group per database and reference.

    The rows of a reference that an open pull request already covers go in a
    group of their own, so the button is offered only for the others.
    """
    groups: Dict[Tuple[Type, str, Optional[int]], List[str]] = {}
    pulls: Dict[int, dict] = {}
    for input_type, row_id, reference in rows:
        pull = pending.get((input_type, row_id))
        number = pull["number"] if pull else None
        if pull:
            pulls[number] = pull
        key = (input_type, (reference or "").strip(), number)
        groups.setdefault(key, []).append(row_id)
    order = list(VERIFIABLE)
    result = []
    for (input_type, reference, number), ids in sorted(
        groups.items(),
        key=lambda item: (
            order.index(item[0][0]),
            item[0][1].lower(),
            item[0][2] or 0,
        ),
    ):
        pull = pulls.get(number) if number is not None else None
        result.append(
            VerificationGroup(
                database=input_type.value,
                reference=reference,
                ids=sorted(ids),
                count=len(ids),
                pending_pr=(
                    VerificationPull(pr_number=pull["number"], pr_url=pull["html_url"])
                    if pull
                    else None
                ),
            )
        )
    return result


@router.get(
    "/verification",
    response_model=VerificationListResponse,
    dependencies=[Depends(require_role(roles.CURATOR))],
)
@limiter.limit("30/minute")
async def list_unverified(
    request: Request, session: AsyncSession = Depends(get_session)
) -> VerificationListResponse:
    """
    The unverified rows of every database, grouped by reference, each with
    the open verification pull request that covers it, if any.
    """
    rows: List[Tuple[Type, str, Optional[str]]] = []
    for input_type, model in VERIFIABLE.items():
        result = await session.execute(
            select(model.id, model.reference).where(
                model.data_curation_status == UNVERIFIED
            )
        )
        rows.extend((input_type, row_id, reference) for row_id, reference in result)
    if not configured():
        return VerificationListResponse(
            configured=False, groups=group_unverified(rows, {})
        )
    pending = pending_verifications(await open_pulls(DataRepoClient()))
    return VerificationListResponse(
        configured=True, groups=group_unverified(rows, pending)
    )


@router.post(
    "/verification",
    response_model=VerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def create_verification(
    request: Request,
    body: VerificationRequest,
    user: User = Depends(require_role(roles.CURATOR)),
) -> VerificationResponse:
    """
    Open a pull request on the data repository that marks ``ids`` as
    verified. Merge it on GitHub (squash). Answers 409 when an id is not in
    the data repository, is already verified there, or is in an open
    verification pull request.
    """
    if not configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is not enabled on this deployment.",
        )
    if body.database not in VERIFIABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{body.database.value} is not a database with a review status.",
        )
    curator = _contributor(user)
    client = DataRepoClient()
    try:
        result = await open_verification(
            body.database,
            body.ids,
            curator,
            pending=pending_verifications(await open_pulls(client)),
            client=client,
        )
    except SubmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
    invalidate_open_pulls()
    return VerificationResponse(
        pr_url=result.pr_url, pr_number=result.pr_number, branch=result.branch
    )
