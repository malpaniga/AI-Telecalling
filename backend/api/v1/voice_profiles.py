from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.core.auth import CurrentUser, get_current_user
from backend.core.rbac import require_platform
from backend.core.db import get_db
from backend.services.voice_profile_service import VoiceProfileService

router=APIRouter(prefix='/voice-profiles', tags=['voice-profiles'])
class CreateProfile(BaseModel): display_name:str; language:str; organization_id:Optional[str]=None
class CreateVersion(BaseModel): routes:dict

@router.get('')
async def list_profiles(user: CurrentUser=Depends(get_current_user)):
    if not user.org_id: raise HTTPException(400, 'No organization')
    return await VoiceProfileService(get_db()).list_customer_profiles(user.org_id)

@router.get('/{profile_id}')
async def get_profile(profile_id:str, user: CurrentUser=Depends(get_current_user)):
    if not user.org_id: raise HTTPException(400, 'No organization')
    profile=await VoiceProfileService(get_db()).get_customer_profile(profile_id,user.org_id)
    if not profile: raise HTTPException(404,'Voice profile not found')
    return profile

@router.post('/admin', dependencies=[Depends(require_platform('platform_owner','platform_admin'))])
async def create_profile(body:CreateProfile):
    return (await VoiceProfileService(get_db()).create_profile(**body.model_dump())).model_dump(by_alias=True)

@router.post('/admin/{profile_id}/versions', dependencies=[Depends(require_platform('platform_owner','platform_admin'))])
async def create_version(profile_id:str, body:CreateVersion):
    try: return (await VoiceProfileService(get_db()).create_version(profile_id,body.routes)).model_dump(by_alias=True)
    except ValueError as exc: raise HTTPException(404,str(exc))
