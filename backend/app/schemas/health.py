from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime


class DatabasePoolHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    process_role: str
    capacity: int
    checked_out: int
    utilisation_percent: float
