from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.profile import Profile, Preferences
from app.schemas.auth import RegisterRequest
from app.core.security import get_password_hash, verify_password


class AuthService:
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower().strip()).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def register_user(db: Session, request: RegisterRequest) -> User:
        existing = AuthService.get_user_by_email(db, request.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        user = User(
            email=request.email.lower().strip(),
            hashed_password=get_password_hash(request.password),
            full_name=request.full_name,
            is_active=True
        )
        db.add(user)
        db.flush()

        # Initialize user's profile and preferences automatically
        profile = Profile(
            user_id=user.id,
            headline="",
            phone="",
            location="",
            bio="",
            links={}
        )
        db.add(profile)
        db.flush()

        preferences = Preferences(
            profile_id=profile.id,
            desired_roles=[],
            preferred_industries=[],
            preferred_locations=[],
            remote_preference="flexible",
            experience_level="mid",
            employment_preference="full-time"
        )
        db.add(preferences)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        user = AuthService.get_user_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive."
            )
        return user
