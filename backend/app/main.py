from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.v1 import auth, questrade, portfolio, trades, settings, recommendations

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(questrade.router, prefix="/api/v1/questrade", tags=["questrade"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])
app.include_router(trades.router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])


@app.get("/")
async def root():
    return {"message": "TSX Trader API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
