from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from models.user import User
from models.user_assessment import UserAssessment, AssessmentStatus
from schemas.user import UserCreate, UserUpdate
from auth.jwt import get_password_hash
import secrets
import string


class UserService:
    @staticmethod
    def get_user_by_id(db:Session,user_id:int)->Optional[User]:
        return db.query(User).filter(User.id==user_id).first()
    
    @staticmethod
    def get_user_by_username(db:Session,username:str)->Optional[User]:
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_users(db:Session,skip:int=0,limit:int=100)->List[User]:
        return db.query(User).offset(skip).limit(limit).all()
    
    @staticmethod
    def create_user(db:Session,user:UserCreate):
        hashed_password=get_password_hash(user.password)
        db_user=User(
            name=user.name,
            role=user.role,
            username=user.username,
            password_hash=hashed_password
        )
        
        # Generate recruiter code if user is a recruiter/admin
        if user.role.lower() in ['admin', 'recruiter']:
            db_user.recruiter_code = UserService.generate_recruiter_code(db)
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update_user(db:Session,user_id:int,user_update:UserUpdate)->Optional[User]:
            db_user=UserService.get_user_by_id(db,user_id)
            if not db_user:
                 return None
            update_data=user_update.dict(exclude_unset=True)
            if "password" in update_data:
                 update_data["password_hash"]=get_password_hash(update_data.pop("password"))
            
            for field,value in update_data.items():
                 setattr(db_user,field,value)
            
            db.commit()
            db.refresh(db_user)
            return db_user
    
    @staticmethod
    def delete_user(db:Session,user_id:int)->bool:
         db_user=UserService.get_user_by_id(db,user_id)
         if not db_user:
              return False
         db.delete()
         db.commit()
         return True
    
    @staticmethod
    def check_username_exists(db:Session,username:str,exclude_id:Optional[int]=None):
        query=db.query(User).filter(User.username==username)
        if exclude_id:
            query=query.filter(User.id!=exclude_id)
        return query.first() is not None

    @staticmethod
    def generate_recruiter_code(db: Session) -> str:
        """Generate a unique 8-character alphanumeric recruiter code."""
        while True:
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            
            # Check if code already exists
            existing_user = db.query(User).filter(User.recruiter_code == code).first()
            if not existing_user:
                return code
    
    @staticmethod
    def validate_recruiter_code(db: Session, recruiter_code: str) -> Optional[User]:
        """Validate a recruiter code and return the recruiter user if valid."""
        if not recruiter_code:
            return None
        
        recruiter = db.query(User).filter(
            and_(
                User.recruiter_code == recruiter_code,
                User.role.in_(['Admin', 'Recruiter'])
            )
        ).first()
        
        return recruiter
    
    @staticmethod
    def link_student_to_recruiter(db: Session, student_id: int, recruiter_id: int) -> bool:
        """Link a student to a recruiter and create UserAssessment entries for all recruiter's assessments."""
        try:
            # Get the recruiter and their assessments
            recruiter = db.query(User).filter(User.id == recruiter_id).first()
            if not recruiter or recruiter.role.lower() not in ['admin', 'recruiter']:
                return False
            
            # Get all assessments created by the recruiter
            from models.assessment import Assessment
            recruiter_assessments = db.query(Assessment).filter(
                Assessment.created_by_user_id == recruiter_id
            ).all()
            
            # Get the student
            student = db.query(User).filter(User.id == student_id).first()
            if not student:
                return False
            
            # Create UserAssessment entries for each assessment
            for assessment in recruiter_assessments:
                # Check if UserAssessment already exists
                existing_ua = db.query(UserAssessment).filter(
                    and_(
                        UserAssessment.user_id == student_id,
                        UserAssessment.recruiter_id == recruiter_id,
                        UserAssessment.assessment_id == assessment.id
                    )
                ).first()
                
                if not existing_ua:
                    ua = UserAssessment(
                        user_id=student_id,
                        recruiter_id=recruiter_id,
                        assessment_id=assessment.id,
                        student_email=student.email,
                        status=AssessmentStatus.INVITED
                    )
                    db.add(ua)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Error linking student to recruiter: {e}")
            return False
    
    @staticmethod
    def get_recruiter_assessments_for_student(db: Session, student_id: int, recruiter_id: int) -> List[dict]:
        """Get all assessments from a specific recruiter that are available to a student."""
        try:
            user_assessments = db.query(UserAssessment).filter(
                and_(
                    UserAssessment.user_id == student_id,
                    UserAssessment.recruiter_id == recruiter_id
                )
            ).all()
            
            result = []
            for ua in user_assessments:
                assessment = ua.assessment
                result.append({
                    'id': assessment.id,
                    'name': assessment.name,
                    'description': assessment.description,
                    'duration': assessment.duration,
                    'status': ua.status.value,
                    'score': ua.score,
                    'start_time': ua.start_time,
                    'end_time': ua.end_time
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting recruiter assessments for student: {e}")
            return []