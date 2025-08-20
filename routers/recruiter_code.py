from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.connection import get_db
from auth.jwt import get_current_user
from models.user import User
from models.user_assessment import UserAssessment
from services.user_service import UserService
from schemas.user import RecruiterCodeLink, RecruiterCodeResponse, RecruiterCodeValidation
from typing import List

router = APIRouter(prefix="/recruiter-code", tags=["Recruiter Code"])

@router.post("/validate", response_model=RecruiterCodeValidation)
def validate_recruiter_code(
    payload: RecruiterCodeLink,
    db: Session = Depends(get_db)
):
    """Validate a recruiter code without linking."""
    recruiter = UserService.validate_recruiter_code(db, payload.recruiter_code)
    
    if not recruiter:
        return RecruiterCodeValidation(
            is_valid=False,
            message="Invalid recruiter code. Please check and try again."
        )
    
    return RecruiterCodeValidation(
        is_valid=True,
        recruiter_name=recruiter.name,
        recruiter_id=recruiter.id,
        message="Valid recruiter code."
    )

@router.post("/link", response_model=RecruiterCodeResponse)
def link_student_to_recruiter(
    payload: RecruiterCodeLink,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Link a student to a recruiter using a recruiter code."""
    # Check if user is a student
    if current_user.role.lower() not in ['student']:
        raise HTTPException(
            status_code=403,
            detail="Only students can link to recruiters."
        )
    
    # Validate recruiter code
    recruiter = UserService.validate_recruiter_code(db, payload.recruiter_code)
    if not recruiter:
        raise HTTPException(
            status_code=400,
            detail="Invalid recruiter code. Please check and try again."
        )
    
    # Check if already linked by looking at UserAssessment entries
    existing_link = db.query(UserAssessment).filter(
        UserAssessment.user_id == current_user.id,
        UserAssessment.recruiter_id == recruiter.id
    ).first()
    
    if existing_link:
        raise HTTPException(
            status_code=400,
            detail="You are already linked to this recruiter."
        )
    
    # Link student to recruiter
    success = UserService.link_student_to_recruiter(
        db, current_user.id, recruiter.id
    )
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to link to recruiter. Please try again."
        )
    
    # Get linked assessments
    linked_assessments = UserService.get_recruiter_assessments_for_student(
        db, current_user.id, recruiter.id
    )
    
    return RecruiterCodeResponse(
        message=f"Successfully linked to {recruiter.name}",
        recruiter_name=recruiter.name,
        recruiter_id=recruiter.id,
        linked_assessments=linked_assessments
    )

@router.get("/my-recruiter")
def get_student_recruiter_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get information about the recruiter the student is linked to."""
    if current_user.role.lower() not in ['student']:
        raise HTTPException(
            status_code=403,
            detail="Only students can access this endpoint."
        )
    
    # Find UserAssessment entries for this student
    user_assessments = db.query(UserAssessment).filter(
        UserAssessment.user_id == current_user.id,
        UserAssessment.recruiter_id.isnot(None)
    ).first()
    
    if not user_assessments:
        return {"message": "No recruiter linked", "recruiter": None}
    
    recruiter = db.query(User).filter(User.id == user_assessments.recruiter_id).first()
    
    return {
        "message": "Recruiter found",
        "recruiter": {
            "id": recruiter.id,
            "name": recruiter.name,
            "email": recruiter.email
        }
    }

@router.get("/recruiter-assessments")
def get_recruiter_assessments_for_student(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all assessments from the recruiter the student is linked to."""
    if current_user.role.lower() not in ['student']:
        raise HTTPException(
            status_code=403,
            detail="Only students can access this endpoint."
        )
    
    # Find UserAssessment entries for this student
    user_assessments = db.query(UserAssessment).filter(
        UserAssessment.user_id == current_user.id,
        UserAssessment.recruiter_id.isnot(None)
    ).first()
    
    if not user_assessments:
        return {"message": "No recruiter linked", "assessments": []}
    
    recruiter_id = user_assessments.recruiter_id
    assessments = UserService.get_recruiter_assessments_for_student(
        db, current_user.id, recruiter_id
    )
    
    return {
        "message": "Assessments retrieved successfully",
        "assessments": assessments
    }
