from pydantic import BaseModel
from datetime import date


class ClaimCreate(BaseModel):
    customer: str
    equipmentModel: str
    serialNumber: str
    description: str
    serviceDate: date
    warrantyStatus: str