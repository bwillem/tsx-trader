from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserSettings
from app.schemas.auth import UserCreate, UserLogin, Token
from app.schemas.user import UserResponse
from app.utils.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(email=user_data.email, hashed_password=hashed_password)
    db.add(user)
    db.flush()

    # Create default settings
    user_settings = UserSettings(
        user_id=user.id,
        position_size_pct=settings.DEFAULT_POSITION_SIZE_PCT,
        stop_loss_pct=settings.DEFAULT_STOP_LOSS_PCT,
        daily_loss_limit_pct=settings.DAILY_LOSS_LIMIT_PCT,
        max_open_positions=settings.MAX_OPEN_POSITIONS,
        min_cash_reserve_pct=settings.MIN_CASH_RESERVE_PCT,
        min_risk_reward_ratio=settings.MIN_RISK_REWARD_RATIO,
        paper_trading_enabled=settings.PAPER_TRADING_MODE,
    )
    db.add(user_settings)
    db.commit()

    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    access_token = create_access_token(data={"sub": user.id})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user
