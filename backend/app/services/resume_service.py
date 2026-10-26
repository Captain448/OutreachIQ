import os
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status

from app.models.user import User
from app.models.resume import Resume, ParsingStatus
from app.models.profile import Skill, SkillStatus, SkillSource
from app.schemas.resume import ResumeUpdate
from app.utils.file_storage import validate_file, save_upload_file, delete_stored_file
from app.services.resume_parser import ResumeParserService
from app.services.profile_service import ProfileService


class ResumeService:
    @staticmethod
    def get_user_resumes(db: Session, user: User) -> List[Resume]:
        return db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()

    @staticmethod
    def get_resume_by_id(db: Session, resume_id: str, user: User) -> Resume:
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found"
            )
        return resume

    @staticmethod
    async def create_resume(
        db: Session,
        user: User,
        file: UploadFile,
        title: Optional[str] = None,
        target_role: Optional[str] = None,
        is_preferred: bool = False
    ) -> Resume:
        ext = validate_file(file)
        
        # Read file bytes
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty"
            )
        
        stored_filename, destination_path, file_size = save_upload_file(content, file.filename or "resume")
        
        # Parse resume text & structure
        parsed_data = ResumeParserService.parse_resume(destination_path, file.filename or "resume")

        # Set default title if not provided
        display_title = title.strip() if title and title.strip() else (os.path.splitext(file.filename or "Resume")[0])
        role = target_role.strip() if target_role and target_role.strip() else "General"

        # Check if user has existing resumes; if not, make this preferred
        existing_count = db.query(Resume).filter(Resume.user_id == user.id).count()
        if existing_count == 0:
            is_preferred = True

        if is_preferred:
            # Unset preferred on all other user resumes
            db.query(Resume).filter(Resume.user_id == user.id).update({"is_preferred": False})

        resume = Resume(
            user_id=user.id,
            title=display_title,
            target_role=role,
            is_preferred=is_preferred,
            is_active=True,
            filename=stored_filename,
            original_filename=file.filename or stored_filename,
            file_path=destination_path,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            parsed_text=parsed_data["parsed_text"],
            parsing_status=parsed_data["parsing_status"],
            parsing_confidence=parsed_data["parsing_confidence"],
            parsing_notes=parsed_data["parsing_notes"],
            extracted_skills=parsed_data["extracted_skills"],
            extracted_education=parsed_data["extracted_education"],
            extracted_experience=parsed_data["extracted_experience"],
            extracted_projects=parsed_data["extracted_projects"],
            raw_metadata=parsed_data["raw_metadata"]
        )
        db.add(resume)

        # Synchronize newly extracted skills into Profile as VERIFIED skills if not present
        profile = ProfileService.get_or_create_profile(db, user)
        existing_skill_names = {s.name.lower() for s in profile.skills}
        for sk in parsed_data["extracted_skills"]:
            if sk["name"].lower() not in existing_skill_names:
                db_skill = Skill(
                    profile_id=profile.id,
                    name=sk["name"],
                    category=sk["category"],
                    status=SkillStatus.VERIFIED,
                    source=SkillSource.RESUME_PARSED,
                    evidence=sk["evidence"],
                    confidence_score=sk["confidence_score"]
                )
                db.add(db_skill)
                existing_skill_names.add(sk["name"].lower())

        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def update_resume(
        db: Session,
        resume_id: str,
        user: User,
        update_data: ResumeUpdate
    ) -> Resume:
        resume = ResumeService.get_resume_by_id(db, resume_id, user)
        
        if update_data.title is not None:
            resume.title = update_data.title
        if update_data.target_role is not None:
            resume.target_role = update_data.target_role
        if update_data.is_active is not None:
            resume.is_active = update_data.is_active
        if update_data.is_preferred is not None:
            if update_data.is_preferred:
                # Unset on others
                db.query(Resume).filter(Resume.user_id == user.id).update({"is_preferred": False})
            resume.is_preferred = update_data.is_preferred

        db.commit()
        db.refresh(resume)
        return resume

    @staticmethod
    def delete_resume(db: Session, resume_id: str, user: User) -> None:
        resume = ResumeService.get_resume_by_id(db, resume_id, user)
        file_path = resume.file_path
        
        db.delete(resume)
        db.commit()

        # Delete physical file
        delete_stored_file(file_path)
