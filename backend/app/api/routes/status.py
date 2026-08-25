from fastapi import APIRouter

from app.services import status_service

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("")
def get_status():
    return status_service.build_status_report()
