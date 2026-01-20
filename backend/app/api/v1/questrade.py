from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.utils.auth import get_current_user
from app.config import get_settings
from app.services.questrade import QuestradeClient
import requests

router = APIRouter()
settings = get_settings()


@router.get("/authorize-url")
async def get_authorize_url(current_user: User = Depends(get_current_user)):
    """Get Questrade OAuth authorization URL"""
    auth_url = (
        f"{settings.QUESTRADE_LOGIN_URL}/oauth2/authorize?"
        f"client_id={settings.QUESTRADE_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={settings.QUESTRADE_REDIRECT_URI}"
    )
    return {"authorize_url": auth_url}


@router.get("/callback")
async def questrade_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Handle Questrade OAuth callback"""
    # Exchange code for tokens
    token_url = f"{settings.QUESTRADE_LOGIN_URL}/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.QUESTRADE_REDIRECT_URI,
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Store tokens
        current_user.questrade_access_token = token_data["access_token"]
        current_user.questrade_refresh_token = token_data["refresh_token"]
        current_user.questrade_api_server = token_data["api_server"]
        from datetime import datetime, timedelta

        expires_in = token_data.get("expires_in", 1800)
        current_user.questrade_token_expires_at = (
            datetime.utcnow() + timedelta(seconds=expires_in)
        ).isoformat()

        db.commit()

        return {"message": "Successfully connected to Questrade"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect: {str(e)}")


@router.get("/accounts")
async def get_accounts(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get Questrade accounts"""
    if not current_user.questrade_access_token:
        raise HTTPException(status_code=400, detail="Questrade not connected")

    try:
        client = QuestradeClient(current_user)
        accounts = client.get_accounts()
        db.commit()  # Commit any token refresh
        return {"accounts": accounts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/positions")
async def get_positions(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get account positions"""
    if not current_user.questrade_access_token:
        raise HTTPException(status_code=400, detail="Questrade not connected")

    try:
        client = QuestradeClient(current_user)
        positions = client.get_account_positions(account_id)
        db.commit()
        return {"positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/balances")
async def get_balances(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get account balances"""
    if not current_user.questrade_access_token:
        raise HTTPException(status_code=400, detail="Questrade not connected")

    try:
        client = QuestradeClient(current_user)
        balances = client.get_account_balances(account_id)
        db.commit()
        return {"balances": balances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disconnect")
async def disconnect_questrade(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Disconnect Questrade account"""
    current_user.questrade_access_token = None
    current_user.questrade_refresh_token = None
    current_user.questrade_api_server = None
    current_user.questrade_token_expires_at = None
    db.commit()
    return {"message": "Questrade disconnected"}
