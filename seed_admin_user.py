#!/usr/bin/env python3
"""
Seed script to create default admin user for knowledgebase management
"""
import sys
import os
from sqlalchemy.orm import Session

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine
from app.models import User
from app.auth_admin import get_password_hash


def create_admin_user():
    """Create default admin user if not exists"""
    db: Session = SessionLocal()
    
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            print("❌ Admin user already exists!")
            print(f"   Username: {existing_admin.username}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Full Name: {existing_admin.full_name}")
            return
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Admin user created successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: admin123")
        print(f"   Full Name: {admin_user.full_name}")
        print("\n⚠️  Please change the default password after first login!")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Creating default admin user...")
    create_admin_user()
