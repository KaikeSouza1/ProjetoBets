from fastapi import APIRouter

from app.api.schemas.lead import LeadIn, LeadOut
from app.services import lead_service

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("", response_model=LeadOut)
def create_lead(lead: LeadIn):
    lead_service.create_lead(lead.name, lead.phone, lead.plan)
    return LeadOut(status="ok")
