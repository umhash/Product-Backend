from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.user import TokenData
import os
from dotenv import load_dotenv

load_dotenv()

# Admin-specific security configuration
ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "admin-secret-key-change-this-in-production")
ADMIN_ALGORITHM = os.getenv("ADMIN_ALGORITHM", "HS256")
ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token bearer for admin
admin_security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_admin_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token for admin"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "admin"})  # Add admin type to token
    encoded_jwt = jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ADMIN_ALGORITHM)
    return encoded_jwt


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(admin_security)) -> TokenData:
    """Verify and decode admin JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, ADMIN_SECRET_KEY, algorithms=[ADMIN_ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "admin":
            raise credentials_exception
            
        token_data = TokenData(email=username)  # Using email field for username
    except JWTError:
        raise credentials_exception
    
    return token_data


def get_current_admin_user(
    token_data: TokenData = Depends(verify_admin_token), 
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated admin user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Look up by username (stored in email field of TokenData)
    user = db.query(User).filter(User.username == token_data.email).first()
    if user is None or not user.is_active or user.role != "admin":
        raise credentials_exception
    
    return user


def authenticate_admin_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate an admin user with username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not user.is_active or user.role != "admin":
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def require_admin_role(current_user: User = Depends(get_current_admin_user)) -> User:
    """Dependency to ensure user has admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
