#!/usr/bin/env python3
"""
Database setup script for StudyCopilot API
This script helps you set up the database and run migrations
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

def check_env_file():
    """Check if .env file exists and has required variables"""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and update with your database credentials:")
        print("cp .env.example .env")
        return False
    
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url or 'username:password' in database_url:
        print("❌ Please update DATABASE_URL in .env file with your actual PostgreSQL credentials")
        return False
    
    print("✅ .env file configured")
    return True

def test_database_connection():
    """Test database connection"""
    try:
        from app.database import engine
        connection = engine.connect()
        connection.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your DATABASE_URL in .env file")
        return False

def run_migrations():
    """Run database migrations"""
    try:
        print("🔄 Running migrations...")
        subprocess.run(['alembic', 'upgrade', 'head'], check=True)
        
        print("✅ Migrations completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return False

def seed_sample_data():
    """Seed sample UK programs data"""
    try:
        print("🔄 Seeding sample UK programs...")
        subprocess.run(['python', 'seed_uk_programs.py'], check=True)
        
        print("✅ Sample data seeded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Seeding failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 StudyCopilot Database Setup")
    print("=" * 40)
    
    # Check environment file
    if not check_env_file():
        sys.exit(1)
    
    # Test database connection
    if not test_database_connection():
        sys.exit(1)
    
    # Run migrations
    if not run_migrations():
        sys.exit(1)
    
    # Seed sample data
    if not seed_sample_data():
        print("⚠️  Warning: Sample data seeding failed, but database is ready")
    
    print("\n🎉 Database setup completed successfully!")
    print("You can now start the API server with: ./start.sh")

if __name__ == "__main__":
    main()
