# Script to assign an assessment to a student by email or user_id
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from models.user import User
from models.assessment import Assessment
from models.user_assessment import UserAssessment, AssessmentStatus

# --- CONFIGURE THESE ---
STUDENT_EMAIL = "student@example.com"  # Change to the student's email
ASSESSMENT_ID = 1                      # Change to the assessment ID to assign

# --- SCRIPT ---
def assign_assessment_to_student(student_email, assessment_id):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == student_email).first()
        if not user:
            print(f"No user found with email: {student_email}")
            return
        assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not assessment:
            print(f"No assessment found with id: {assessment_id}")
            return
        # Check if already assigned
        existing = db.query(UserAssessment).filter_by(user_id=user.id, assessment_id=assessment.id).first()
        if existing:
            print("Assessment already assigned to this student.")
            return
        ua = UserAssessment(
            user_id=user.id,
            assessment_id=assessment.id,
            status=AssessmentStatus.PENDING
        )
        db.add(ua)
        db.commit()
        print(f"Assigned assessment {assessment_id} to {student_email}.")
    finally:
        db.close()

if __name__ == "__main__":
    assign_assessment_to_student(STUDENT_EMAIL, ASSESSMENT_ID)
