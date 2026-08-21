"""
Router for Social Media & Advertising Competitor Benchmarking.
Uses Instagram Business Discovery API and Meta Page/Ad Library APIs.
"""
import logging
from fastapi import APIRouter, Depends
from app.middleware.auth import verify_api_key
from app.models.benchmarking import BenchmarkingRequest, BenchmarkingResponse
from app.services.benchmarking import benchmarking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/benchmarking", tags=["Benchmarking"])


@router.post("", response_model=BenchmarkingResponse, dependencies=[Depends(verify_api_key)])
async def get_benchmarking(request: BenchmarkingRequest):
    """
    Run competitive benchmarking across Instagram and Facebook competitors.
    Returns sorted competitors by followers descending, with engagement rates and ad counts.
    """
    logger.info(
        f"Benchmarking requested for {len(request.instagram_competitors)} IG and "
        f"{len(request.facebook_competitors)} FB competitors"
    )
    return await benchmarking_service.run_benchmarking(request)
