#!/usr/bin/env python3
"""
Simple database migration script to add recruiter_code column to users table.
This script avoids model import issues by using raw SQL.
"""

import sys
from sqlalchemy import text
from database.connection import engine

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

def generate_simple_recruiter_codes():
    """Generate simple recruiter codes for existing admin/recruiter users."""
    try:
        with engine.connect() as connection:
            # Find users without recruiter codes who are admins or recruiters
            result = connection.execute(text("""
                SELECT id, name, role 
                FROM users 
                WHERE recruiter_code IS NULL 
                AND LOWER(role) IN ('admin', 'recruiter')
            """))
            
            users_without_codes = result.fetchall()
            
            if not users_without_codes:
                print("✅ All existing admin/recruiter users already have recruiter codes")
                return True
            
            print(f"📝 Generating recruiter codes for {len(users_without_codes)} existing users...")
            
            import secrets
            import string
            
            for user in users_without_codes:
                # Generate unique 8-character alphanumeric code
                while True:
                    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                    
                    # Check if code already exists
                    existing = connection.execute(text("""
                        SELECT id FROM users WHERE recruiter_code = :code
                    """), {"code": code}).fetchone()
                    
                    if not existing:
                        break
                
                # Update user with new code
                connection.execute(text("""
                    UPDATE users SET recruiter_code = :code WHERE id = :user_id
                """), {"code": code, "user_id": user.id})
                
                print(f"   - {user.name} ({user.role}): {code}")
            
            connection.commit()
            print("✅ Successfully generated recruiter codes for existing users")
            return True
            
    except Exception as e:
        print(f"❌ Error generating recruiter codes: {e}")
        return False

def main():
    """Main migration function."""
    print("🚀 Starting simple database migration for recruiter_code column...")
    
    # Step 1: Add the column
    if not add_recruiter_code_column():
        print("❌ Migration failed at step 1")
        sys.exit(1)
    
    # Step 2: Generate codes for existing users
    if not generate_simple_recruiter_codes():
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

