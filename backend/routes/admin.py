import asyncio
import json
from queue import Empty, Queue
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from schemas import ReviewInput
from services.admin_service import admin_stats, evaluation, resolve_review, review_queue
from services.auth import require_admin
from services.live_feed import subscribe, unsubscribe

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/v1/admin/reviews")
def get_reviews(
    status: Literal["pending", "reviewed", "all"] = "pending",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return review_queue(status, limit, offset)


@router.post("/v1/admin/reviews/{check_id}")
def post_review(check_id: UUID, payload: ReviewInput):
    return resolve_review(str(check_id), payload)


@router.get("/v1/admin/stats")
def get_admin_stats():
    return admin_stats()


@router.get("/v1/admin/evaluation")
def get_evaluation():
    return evaluation()


async def _events(subscriber: Queue[dict[str, Any]]):
    try:
        while True:
            try:
                item = await asyncio.to_thread(subscriber.get, True, 15)
            except Empty:
                yield ": keepalive\n\n"
                continue
            event_id = str(item.get("check_id", ""))
            data = json.dumps(item, separators=(",", ":"), ensure_ascii=False)
            yield f"id: {event_id}\nevent: check\ndata: {data}\n\n"
    finally:
        unsubscribe(subscriber)


@router.get("/v1/admin/feed")
async def admin_feed():
    subscriber = subscribe()
    return StreamingResponse(
        _events(subscriber),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
