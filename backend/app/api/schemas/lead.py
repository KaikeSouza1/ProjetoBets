from pydantic import BaseModel, Field


class LeadIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=10, max_length=15, pattern=r"^\d+$")
    plan: str = Field(pattern=r"^(gratis|pro)$")


class LeadOut(BaseModel):
    status: str
