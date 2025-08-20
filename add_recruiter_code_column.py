#!/usr/bin/env python3
"""
Database migration script to add recruiter_code column to users table.
This script should be run after updating the User model to add the new column.
"""

import sys
import os
from sqlalchemy import text
from database.connection import engine, SessionLocal

def add_recruiter_code_column():
    """Add recruiter_code column to users table if it doesn't exist."""
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'recruiter_code'
            """))
            
            if result.fetchone():
                print("✅ recruiter_code column already exists in users table")
                return True
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN recruiter_code VARCHAR UNIQUE
            """))
            
            # Create index on the new column
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_users_recruiter_code ON users(recruiter_code)
            """))
            
            connection.commit()
            print("✅ Successfully added recruiter_code column to users table")
            return True
            
    except Exception as e:
        print(f"❌ Error adding recruiter_code column: {e}")
        return False

def generate_recruiter_codes_for_existing_users():
    """Generate recruiter codes for existing admin/recruiter users."""
    try:
        db = SessionLocal()
        
        # Import models here to avoid circular import issues
        from models.user import User
        
        # Find users without recruiter codes who are admins or recruiters
        users_without_codes = db.query(User).filter(
            User.recruiter_code.is_(None),
            User.role.in_(['Admin', 'Recruiter', 'admin', 'recruiter'])
        ).all()
        
        if not users_without_codes:
            print("✅ All existing admin/recruiter users already have recruiter codes")
            return True
        
        print(f"📝 Generating recruiter codes for {len(users_without_codes)} existing users...")
        
        # Import UserService here to avoid circular imports
        from services.user_service import UserService
        
        for user in users_without_codes:
            # Generate unique recruiter code
            recruiter_code = UserService.generate_recruiter_code(db)
            user.recruiter_code = recruiter_code
            print(f"   - {user.name} ({user.role}): {recruiter_code}")
        
        db.commit()
        print("✅ Successfully generated recruiter codes for existing users")
        return True
        
    except Exception as e:
        print(f"❌ Error generating recruiter codes: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main migration function."""
    print("🚀 Starting database migration for recruiter_code column...")
    
    # Step 1: Add the column
    if not add_recruiter_code_column():
        print("❌ Migration failed at step 1")
        sys.exit(1)
    
    # Step 2: Generate codes for existing users
    if not generate_recruiter_codes_for_existing_users():
        print("❌ Migration failed at step 2")
        sys.exit(1)
    
    print("🎉 Database migration completed successfully!")
    print("\n📋 Summary of changes:")
    print("   - Added recruiter_code column to users table")
    print("   - Created index on recruiter_code column")
    print("   - Generated unique recruiter codes for existing admin/recruiter users")
    print("\n💡 New users with Admin or Recruiter roles will automatically get recruiter codes")

if __name__ == "__main__":
    main()
