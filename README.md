# StudyCopilot - Backend API

FastAPI backend for StudyCopilot - Your AI-Powered Path to UK Universities.

## Prerequisites

- Python 3.8+
- PostgreSQL database (running in Docker or locally)

## Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Configuration
```bash
# Copy environment template
cp .env.example .env

# Generate a secure secret key
python generate_secret_key.py

# Update .env with your PostgreSQL credentials and secret key
```

### 4. Database Setup
```bash
# Run the database setup script
python setup_database.py
```

### 5. Start Development Server
```bash
# Using the start script
./start.sh

# Or manually
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

- Interactive API docs: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`

## Project Structure

```
product-be/
├── app/
│   ├── api/              # API routes
│   │   └── auth.py       # Authentication endpoints
│   ├── models/           # Database models
│   │   └── student.py    # Student model
│   ├── schemas/          # Pydantic schemas
│   │   └── student.py    # Student schemas
│   ├── database.py       # Database configuration
│   └── auth.py          # Authentication utilities
├── alembic/             # Database migrations
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create from .env.example)
├── .env.example         # Environment template
├── generate_secret_key.py  # Secret key generator
└── setup_database.py   # Database setup script
```

## Environment Variables

Required variables in `.env`:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT token signing key (generate with `python generate_secret_key.py`)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: 30)
- `ALLOWED_ORIGINS`: CORS allowed origins (default: http://localhost:3000)

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# View migration history
alembic history
```

## Authentication

The API uses JWT tokens for authentication:
- `/auth/signup` - Register new student
- `/auth/login` - Authenticate student
- `/auth/me` - Get current user info (requires token)
