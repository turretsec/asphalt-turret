from fastapi import APIRouter

from asphalt_turret_api.schemas.volume import VolumeResponse
from asphalt_turret_engine.adapters.volumes import list_removable_volumes

router = APIRouter(prefix="/volumes", tags=["volumes"])

@router.get("", response_model=list[VolumeResponse])
def get_removable_volumes():
    """
    Get a list of removable volumes connected to the system.
    """
    return list_removable_volumes()