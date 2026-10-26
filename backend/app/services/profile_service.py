from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.profile import (
    Profile, Preferences, Education, WorkExperience, Project, Skill, SkillStatus, SkillSource
)
from app.schemas.profile import ProfileUpdate


class ProfileService:
    @staticmethod
    def get_or_create_profile(db: Session, user: User) -> Profile:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
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

            pref = Preferences(
                profile_id=profile.id,
                desired_roles=[],
                preferred_industries=[],
                preferred_locations=[],
                remote_preference="flexible",
                experience_level="mid",
                employment_preference="full-time"
            )
            db.add(pref)
            db.commit()
            db.refresh(profile)
        return profile

    @staticmethod
    def calculate_completeness(profile: Profile, user: User) -> int:
        score = 0
        total_parts = 7

        # 1. Basic Info (Name, headline, location, phone)
        has_basic = bool(user.full_name and (profile.headline or profile.location))
        if has_basic:
            score += 1

        # 2. Bio / Summary
        if profile.bio and len(profile.bio.strip()) > 20:
            score += 1

        # 3. Education
        if profile.education and len(profile.education) > 0:
            score += 1

        # 4. Work Experience
        if profile.work_experience and len(profile.work_experience) > 0:
            score += 1

        # 5. Projects
        if profile.projects and len(profile.projects) > 0:
            score += 1

        # 6. Skills
        if profile.skills and len(profile.skills) > 0:
            score += 1

        # 7. Preferences (desired roles or remote pref)
        if profile.preferences and (len(profile.preferences.desired_roles) > 0 or profile.preferences.preferred_locations):
            score += 1

        return int((score / total_parts) * 100)

    @staticmethod
    def update_profile(db: Session, user: User, update_data: ProfileUpdate) -> Profile:
        profile = ProfileService.get_or_create_profile(db, user)

        # Update User full name if provided
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
            db.add(user)

        # Update Profile basic fields
        if update_data.headline is not None:
            profile.headline = update_data.headline
        if update_data.phone is not None:
            profile.phone = update_data.phone
        if update_data.location is not None:
            profile.location = update_data.location
        if update_data.bio is not None:
            profile.bio = update_data.bio
        if update_data.links is not None:
            profile.links = update_data.links

        # Update Preferences
        if update_data.preferences is not None:
            pref = profile.preferences
            if not pref:
                pref = Preferences(profile_id=profile.id)
                db.add(pref)
            pref.desired_roles = update_data.preferences.desired_roles
            pref.preferred_industries = update_data.preferences.preferred_industries
            pref.preferred_locations = update_data.preferences.preferred_locations
            pref.remote_preference = update_data.preferences.remote_preference
            pref.experience_level = update_data.preferences.experience_level
            pref.employment_preference = update_data.preferences.employment_preference

        # Update Education list if explicitly provided
        if update_data.education is not None:
            # Replace collection cleanly
            db.query(Education).filter(Education.profile_id == profile.id).delete()
            for edu in update_data.education:
                new_edu = Education(
                    profile_id=profile.id,
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_year=edu.start_year,
                    graduation_year=edu.graduation_year,
                    grade_or_gpa=edu.grade_or_gpa,
                    details=edu.details
                )
                db.add(new_edu)

        # Update Work Experience list if explicitly provided
        if update_data.work_experience is not None:
            db.query(WorkExperience).filter(WorkExperience.profile_id == profile.id).delete()
            for exp in update_data.work_experience:
                new_exp = WorkExperience(
                    profile_id=profile.id,
                    company=exp.company,
                    role=exp.role,
                    location=exp.location,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    description=exp.description,
                    technologies=exp.technologies
                )
                db.add(new_exp)

        # Update Projects list if explicitly provided
        if update_data.projects is not None:
            db.query(Project).filter(Project.profile_id == profile.id).delete()
            for proj in update_data.projects:
                new_proj = Project(
                    profile_id=profile.id,
                    title=proj.title,
                    description=proj.description,
                    technologies=proj.technologies,
                    role_contribution=proj.role_contribution,
                    github_url=proj.github_url,
                    demo_url=proj.demo_url
                )
                db.add(new_proj)

        # Update Skills list if explicitly provided
        if update_data.skills is not None:
            db.query(Skill).filter(Skill.profile_id == profile.id).delete()
            for sk in update_data.skills:
                new_sk = Skill(
                    profile_id=profile.id,
                    name=sk.name,
                    category=sk.category,
                    status=sk.status,
                    source=sk.source,
                    evidence=sk.evidence,
                    confidence_score=sk.confidence_score
                )
                db.add(new_sk)

        db.commit()
        db.refresh(profile)
        return profile
