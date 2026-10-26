from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeUpdate
from app.services.resume_service import ResumeService

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.get("", response_model=List[ResumeRead])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ResumeService.get_user_resumes(db, current_user)


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    target_role: Optional[str] = Form("General"),
    is_preferred: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await ResumeService.create_resume(
        db=db,
        user=current_user,
        file=file,
        title=title,
        target_role=target_role,
        is_preferred=is_preferred
    )


@router.get("/{resume_id}", response_model=ResumeRead)
def get_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ResumeService.get_resume_by_id(db, resume_id, current_user)


@router.put("/{resume_id}", response_model=ResumeRead)
def update_resume(
    resume_id: str,
    update_data: ResumeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ResumeService.update_resume(db, resume_id, current_user, update_data)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ResumeService.delete_resume(db, resume_id, current_user)
    return None
