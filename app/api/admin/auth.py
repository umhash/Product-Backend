from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.user import UserLogin, AdminToken, UserResponse
from app.auth_admin import authenticate_admin_user, create_admin_access_token, get_current_admin_user
from datetime import timedelta
import os

router = APIRouter(prefix="/admin/auth", tags=["Admin Authentication"])

ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))


@router.post("/login", response_model=AdminToken)
async def admin_login(login_data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate and login an admin user"""
    
    # Authenticate admin user
    user = authenticate_admin_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive account"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_admin_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    # Convert to response model
    user_response = UserResponse.model_validate(user)
    
    return AdminToken(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
async def get_current_admin_info(current_user: User = Depends(get_current_admin_user)):
    """Get current authenticated admin user information"""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def admin_logout():
    """Logout admin user (client should remove token)"""
    return {"message": "Successfully logged out"}
