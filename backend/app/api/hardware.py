import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user
from app.database import get_db
from app.models.hardware_profile import HardwareProfile
from app.schemas.node import HardwareProfileOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/hardware", tags=["hardware"])


@router.get("/", response_model=list[HardwareProfileOut])
async def list_hardware(
    db: AsyncSession = Depends(get_db), user: dict | None = Depends(get_optional_user)
):
    result = await db.execute(select(HardwareProfile).order_by(HardwareProfile.name))
    profiles = result.scalars().all()
    logger.debug("Listed %d hardware profiles", len(profiles))
    return profiles
