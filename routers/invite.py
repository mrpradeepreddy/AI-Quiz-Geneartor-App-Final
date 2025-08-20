# In file: routers/invites.py
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from schemas.invite import InviteCreate # Make sure to import your schema
from models.invite_token import InviteToken
from models.user_assessment import UserAssessment, AssessmentStatus
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
from database.connection import get_db
from schemas.invite_token import InviteTokenResponse
from models.user import User
from auth.jwt import get_current_user
from utils.email import send_invite_email

# Define your frontend URL (replace with your actual domain later)
FRONTEND_URL = "http://localhost:8501"

router = APIRouter(prefix="/invites", tags=["Invitations"])

@router.post("/send")
async def send_quiz_invite(
    payload: InviteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_recruiter: User = Depends(get_current_user)
):
    """Send quiz invitations to students with improved link generation."""
    # Validate that the recruiter has a recruiter code
    if not current_recruiter.recruiter_code:
        raise HTTPException(
            status_code=400, 
            detail="Recruiter code not found. Please contact support."
        )
    
    # Validate that the assessment exists and belongs to the recruiter
    from models.assessment import Assessment
    assessment = db.query(Assessment).filter(
        Assessment.id == payload.assessment_id,
        Assessment.created_by_user_id == current_recruiter.id
    ).first()
    
    if not assessment:
        raise HTTPException(
            status_code=404, 
            detail="Assessment not found or you don't have permission to invite students to it."
        )
    
    successful_invites = 0
    failed_invites = []
    
    for student_email in payload.emails:
        try:
            # Generate a secure random token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(days=7)  # Extended to 7 days
            
            # Store token in DB
            invite_token = InviteToken(
                token=token,
                assessment_id=payload.assessment_id,
                student_email=student_email,
                used=False,
                expires_at=expires_at
            )
            db.add(invite_token)
            db.commit()
            
            # Generate invitation link with both invite token and recruiter code
            invitation_link = f"{FRONTEND_URL}/?invite={token}&recruiter_code={current_recruiter.recruiter_code}"
            
            # Send email in background
            background_tasks.add_task(
                send_invite_email,
                recipient_email=student_email,
                recruiter=current_recruiter,
                invitation_link=invitation_link
            )
            
            successful_invites += 1
            
        except Exception as e:
            failed_invites.append({"email": student_email, "error": str(e)})
            db.rollback()
            continue
    
    # Return detailed results
    result = {
        "message": f"Invitations processed: {successful_invites} successful, {len(failed_invites)} failed",
        "successful_count": successful_invites,
        "failed_count": len(failed_invites),
        "failed_invites": failed_invites
    }
    
    if failed_invites:
        result["warning"] = "Some invitations failed to send. Check the failed_invites list for details."
    
    return result

@router.get("/validate/{token}", response_model=InviteTokenResponse)
def validate_invite_token(token: str, db: Session = Depends(get_db)):
    """Validate an invite token and return assessment info."""
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        raise HTTPException(
            status_code=400, 
            detail="Invalid invitation token. Please check the link and try again."
        )
    
    if invite.used:
        raise HTTPException(
            status_code=400, 
            detail="This invitation has already been used."
        )
    
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400, 
            detail="This invitation has expired. Please request a new one."
        )
    
    # Fetch assessment and questions
    from models.assessment import Assessment
    assessment = db.query(Assessment).filter_by(id=invite.assessment_id).first()
    
    if not assessment:
        raise HTTPException(
            status_code=404, 
            detail="Assessment not found for this invitation."
        )
    
    # Get questions
    questions = []
    for aq in assessment.assessment_questions:
        q = aq.question
        questions.append({"id": q.id, "text": q.question_text})
    
    return InviteTokenResponse(
        title=assessment.name,
        questions=questions,
        duration=assessment.duration,
        assessment_id=assessment.id
    )

@router.post("/accept/{token}")
def accept_invite_token(token: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Accept an invite: link student to recruiter and assessment, mark invite as used."""
    # Validate the invite token
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        raise HTTPException(
            status_code=400, 
            detail="Invalid invitation token. Please check the link and try again."
        )
    
    if invite.used:
        raise HTTPException(
            status_code=400, 
            detail="This invitation has already been used."
        )
    
    if invite.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400, 
            detail="This invitation has expired. Please request a new one."
        )
    
    # Find the recruiter (admin) who created the assessment
    from models.assessment import Assessment
    assessment = db.query(Assessment).filter_by(id=invite.assessment_id).first()
    
    if not assessment:
        raise HTTPException(
            status_code=404, 
            detail="Assessment not found for this invitation."
        )
    
    recruiter_id = assessment.created_by_user_id
    
    # Check if UserAssessment already exists for this student, recruiter, and assessment
    existing_ua = db.query(UserAssessment).filter_by(
        user_id=current_user.id,
        recruiter_id=recruiter_id,
        assessment_id=invite.assessment_id
    ).first()
    
    if existing_ua:
        # Mark invite as used even if already linked
        invite.used = True
        db.commit()
        return {"message": "You are already linked to this assessment."}
    
    try:
        # Create UserAssessment
        ua = UserAssessment(
            user_id=current_user.id,
            recruiter_id=recruiter_id,
            assessment_id=invite.assessment_id,
            student_email=current_user.email,
            status=AssessmentStatus.INVITED,
            start_time=None,
            end_time=None
        )
        db.add(ua)
        
        # Mark invite as used
        invite.used = True
        
        db.commit()
        
        return {
            "message": "Invitation accepted successfully! Assessment assigned.",
            "assessment_name": assessment.name,
            "recruiter_id": recruiter_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to accept invitation: {str(e)}"
        )

@router.get("/status/{token}")
def get_invite_status(token: str, db: Session = Depends(get_db)):
    """Get the status of an invitation token without requiring authentication."""
    invite = db.query(InviteToken).filter(InviteToken.token == token).first()
    
    if not invite:
        return {
            "valid": False,
            "message": "Invalid invitation token",
            "status": "invalid"
        }
    
    if invite.used:
        return {
            "valid": False,
            "message": "This invitation has already been used",
            "status": "used"
        }
    
    if invite.expires_at < datetime.utcnow():
        return {
            "valid": False,
            "message": "This invitation has expired",
            "status": "expired"
        }
    
    # Get assessment info
    from models.assessment import Assessment
    assessment = db.query(Assessment).filter_by(id=invite.assessment_id).first()
    
    if not assessment:
        return {
            "valid": False,
            "message": "Assessment not found for this invitation",
            "status": "assessment_not_found"
        }
    
    return {
        "valid": True,
        "message": "Invitation is valid",
        "status": "valid",
        "assessment_name": assessment.name,
        "student_email": invite.student_email,
        "expires_at": invite.expires_at.isoformat()
    }