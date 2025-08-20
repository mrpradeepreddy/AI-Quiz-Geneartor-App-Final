# routers/user_assessment.py

# --- 1. Imports (Grouped and Organized) ---
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone

# Database and Models
from database.connection import get_db
from models.user import User
from models.assessment import Assessment
from models.question import Question
from models.choice import Choice
from models.user_assessment import UserAssessment, AssessmentStatus
from models.user_answer import UserAnswer

# Schemas
from schemas.user_assessment import UserAssessment as UserAssessmentSchema, AssessmentSubmission, AssessmentResult
from schemas.user_assessment import UserAnswer as UserAnswerSchema

# Security / Dependencies
from auth.jwt import require_recruiter, require_student, get_current_user

# --- 2. Router Definition (Create the router instance) ---
router = APIRouter(
    prefix="/user_assessments",
    tags=["User Assessments"]
)

# --- 3. API Endpoints ---

@router.post("/start", response_model=UserAssessmentSchema)
async def start_assessment(
    assessment_id: int,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Start an assessment for the currently logged-in student."""
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )

    active_assessment = db.query(UserAssessment).filter(
        UserAssessment.user_id == current_user.id,
        UserAssessment.assessment_id == assessment_id,
        UserAssessment.status == AssessmentStatus.STARTED
    ).first()

    if active_assessment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active assessment for this test"
        )

    user_assessment = UserAssessment(
        user_id=current_user.id,
        assessment_id=assessment_id,
        start_time=datetime.now(timezone.utc),
        status=AssessmentStatus.STARTED
    )
    db.add(user_assessment)
    db.commit()
    db.refresh(user_assessment)
    return user_assessment


@router.post("/{user_assessment_id}/submit", response_model=AssessmentResult)
async def submit_assessment(
    user_assessment_id: int,
    submission: AssessmentSubmission,
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Submit answers for an assessment and calculate the score."""
    user_assessment = db.query(UserAssessment).options(
        joinedload(UserAssessment.assessment).selectinload(Assessment.assessment_questions)
    ).filter(
        UserAssessment.id == user_assessment_id,
        UserAssessment.user_id == current_user.id
    ).first()

    if not user_assessment:
        raise HTTPException(status_code=404, detail="User assessment not found")
    if user_assessment.status == AssessmentStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Assessment already completed")

    time_elapsed = datetime.now(timezone.utc) - user_assessment.start_time
    if time_elapsed.total_seconds() > user_assessment.assessment.duration * 60:
        raise HTTPException(status_code=400, detail="Assessment time has expired")

    question_ids = [q.question_id for q in user_assessment.assessment.assessment_questions]
    questions_map = {q.id: q for q in db.query(Question).filter(Question.id.in_(question_ids)).all()}
    correct_choices_map = {c.question_id: c.id for c in db.query(Choice).filter(Choice.question_id.in_(question_ids), Choice.iss_correct == True).all()}

    total_score = 0
    total_marks = sum(q.marks for q in questions_map.values())
    
    answers_to_add = []
    for answer_data in submission.answers:
        question_id = answer_data.question_id
        selected_choice_id = answer_data.selected_choice_id
        correct_choice_id = correct_choices_map.get(question_id)
        is_correct = (selected_choice_id is not None and selected_choice_id == correct_choice_id)
        
        if is_correct:
            total_score += questions_map[question_id].marks

        answers_to_add.append(UserAnswer(
            user_assessment_id=user_assessment_id,
            question_id=question_id,
            selected_choice_id=selected_choice_id,
            is_correct=is_correct
        ))
    
    db.add_all(answers_to_add) # More efficient way to add multiple objects

    user_assessment.score = total_score
    user_assessment.end_time = datetime.now(timezone.utc)
    user_assessment.status = AssessmentStatus.COMPLETED

    db.commit()
    db.refresh(user_assessment)

    percentage = (total_score / total_marks * 100) if total_marks > 0 else 0
    return AssessmentResult(
        user_assessment_id=user_assessment_id,
        score=total_score,
        total_questions=len(question_ids),
        total_marks=total_marks,
        percentage=percentage,
        completed_at=user_assessment.end_time
    )


@router.get("/statistics", summary="Get Global Assessment Statistics")
async def get_assessment_statistics(
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    """Get overall assessment statistics (recruiter only)."""
    total_assessments = db.query(UserAssessment).count()
    completed_assessments = db.query(UserAssessment).filter(UserAssessment.status == "Completed").count()
    avg_score_result = db.query(func.avg(UserAssessment.score)).filter(UserAssessment.status == AssessmentStatus.COMPLETED).scalar()

    return {
        "total_assessments_taken": total_assessments,
        "completed_assessments": completed_assessments,
        "average_score": round(avg_score_result, 2) if avg_score_result else 0,
        "completion_rate": (completed_assessments / total_assessments * 100) if total_assessments > 0 else 0
    }


@router.get("/recruiter/students", summary="Get Students Assigned by Recruiter")
def get_students_for_recruiter(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter)
):
    """Returns a summary of all students assigned assessments by the current recruiter (recruiter)."""
    user_assessments = db.query(UserAssessment).options(
        joinedload(UserAssessment.user), 
        joinedload(UserAssessment.assessment) # Eager load assessment details
    ).filter(
        UserAssessment.recruiter_id == current_user.id
    ).all()

    student_stats = {}
    for ua in user_assessments:
        if ua.user is None:
            continue
        student_id = ua.user.id
        if student_id not in student_stats:
            student_stats[student_id] = {
                "student_id": student_id,
                "student_name": ua.user.name,
                "student_email": ua.user.email,
                "assessments": [],
                "total_completed": 0,
                "total_assigned": 0,
                "average_score": 0.0
            }
        
        student_stats[student_id]["assessments"].append({
            "assessment_id": ua.assessment_id,
            "assessment_name": ua.assessment.name if ua.assessment else "N/A",
            "status": ua.status,
            "score": ua.score
        })
        student_stats[student_id]["total_assigned"] += 1
        if ua.status == "Completed" and ua.score is not None:
            student_stats[student_id]["total_completed"] += 1
    
    for s_id, stats in student_stats.items():
        scores = [a["score"] for a in stats["assessments"] if a["score"] is not None]
        stats["average_score"] = sum(scores) / len(scores) if scores else 0.0

    return list(student_stats.values())


@router.get("/recruiter/stats", summary="Get summary stats for current recruiter")
def get_recruiter_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter)
):
    """Aggregated stats: attempted vs not, completed, passed vs failed using 50% threshold."""
    user_assessments = db.query(UserAssessment).options(
        joinedload(UserAssessment.assessment).selectinload(Assessment.assessment_questions)
    ).filter(UserAssessment.recruiter_id == current_user.id).all()

    total_assigned = len(user_assessments)
    attempted = sum(1 for ua in user_assessments if ua.status in [AssessmentStatus.STARTED, AssessmentStatus.COMPLETED])
    completed = sum(1 for ua in user_assessments if ua.status == AssessmentStatus.COMPLETED)

    passed = 0
    failed = 0
    for ua in user_assessments:
        if ua.status != AssessmentStatus.COMPLETED or ua.score is None or not ua.assessment:
            continue
        # compute total marks for this assessment
        question_ids = [aq.question_id for aq in ua.assessment.assessment_questions]
        if not question_ids:
            continue
        total_marks = db.query(func.sum(Question.marks)).filter(Question.id.in_(question_ids)).scalar() or 0
        if total_marks == 0:
            continue
        percentage = (ua.score / total_marks) * 100.0
        if percentage >= 50.0:
            passed += 1
        else:
            failed += 1

    return {
        "total_assigned": total_assigned,
        "attempted": attempted,
        "not_attempted": total_assigned - attempted,
        "completed": completed,
        "passed": passed,
        "failed": failed,
    }


@router.get("/students/me/assessments")
def get_my_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """Return the current student's assigned assessments with status and score percentage."""
    records = db.query(UserAssessment).options(
        joinedload(UserAssessment.assessment).selectinload(Assessment.assessment_questions)
    ).filter(UserAssessment.user_id == current_user.id).all()
    result = []
    for ua in records:
        total_marks = 0
        if ua.assessment:
            qids = [aq.question_id for aq in ua.assessment.assessment_questions]
            if qids:
                total_marks = db.query(func.sum(Question.marks)).filter(Question.id.in_(qids)).scalar() or 0
        percentage = None
        if ua.score is not None and total_marks:
            percentage = (ua.score / total_marks) * 100.0
        result.append({
            "assessment_id": ua.assessment_id,
            "assessment_name": ua.assessment.name if ua.assessment else "Assessment",
            "status": ua.status.value if hasattr(ua.status, 'value') else str(ua.status),
            "score": percentage
        })
    return result


@router.get("/{user_assessment_id}/answers", response_model=List[UserAnswerSchema])
async def get_user_answers(
    user_assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all answers for a specific user assessment (owner or recruiter)."""
    user_assessment = db.query(UserAssessment).filter(UserAssessment.id == user_assessment_id).first()
    if not user_assessment:
        raise HTTPException(status_code=404, detail="User assessment not found")

    if (current_user.role.lower() not in ['recruiter','admin']) and (user_assessment.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return db.query(UserAnswer).filter(UserAnswer.user_assessment_id == user_assessment_id).all()