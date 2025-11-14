"""
Kraken AI Trading Bot - FastAPI Application
Generated from AI Agent Master Template
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="Kraken AI Trading Bot",
    description="Automated swing trading bot for Bitcoin using Kraken Spot API with AI validation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("../frontend/static"):
    app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

@app.get("/")
async def root():
    return {"message": "Kraken AI Trading Bot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Kraken AI Trading Bot"}

# API routes
@app.get("/api/v1/status")
async def api_status():
    return {"api_version": "1.0.0", "status": "active"}

@app.get("/api/v1/bot/status")
async def bot_status():
    """Get current bot trading status"""
    return {
        "bot_running": True,
        "btc_position": 0.0,
        "trailing_stop": None,
        "last_trade": None,
        "balance_usd": 0.0
    }

@app.post("/api/v1/bot/start")
async def start_bot():
    """Start the trading bot"""
    return {"message": "Bot started", "status": "running"}

@app.post("/api/v1/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    return {"message": "Bot stopped", "status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
