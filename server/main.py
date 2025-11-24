# backend/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import config
from graph import create_graph
from tools.whatsapp import router as whatsapp_router
from web.routes import router as web_router           # ← Clean WebSocket routes
from auth.routes import router as auth_router         # ← JWT + Google login

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("refugee-agent")

# FastAPI App
app = FastAPI(
    title="Refugee First – 72-Hour Survival Agent",
    description="Real-time, multilingual, location-aware emergency support for refugees.",
    version="1.0.0",
    docs_url="/docs" if config.DEBUG else None,
    redoc_url=None,
)

# CORS — dev: allow all, prod: only your real frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if config.DEBUG else [
        "https://refugeefirst.org",
        "https://www.refugeefirst.org",
        "https://app.refugeefirst.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated PDFs
app.mount(
    "/downloads",
    StaticFiles(directory=str(config.PDF_OUTPUT_PATH)),
    name="pdfs"
)

# === ROUTES ===
app.include_router(auth_router)        # /auth/login, /auth/signup, /auth/login/google
app.include_router(whatsapp_router, prefix="/whatsapp")  # Twilio webhook
app.include_router(web_router)         # /ws/{session_id} ← clean WebSocket

# Load LangGraph once at startup
try:
    graph = create_graph()
    logger.info("LangGraph workflow loaded successfully")
except Exception as e:
    logger.critical(f"Failed to initialize LangGraph: {e}")
    raise


# Health check + beautiful root
@app.get("/")
async def root():
    return {
        "status": "ACTIVE",
        "message": "Refugee First Agent is running and ready to save lives",
        "features": [
            "130+ languages",
            "Real-time OSM shelters, food, medical",
            "Asylum & legal guidance",
            "Offline PDF survival plans",
            "WhatsApp + Web Chat + Google Login"
        ],
        "endpoints": {
            "web_chat": "wss://yourdomain.com/ws/{session_id}",
            "whatsapp": "/whatsapp",
            "auth": "/auth/login | /auth/login/google",
            "pdfs": "/downloads/{session_id}.pdf"
        },
        "version": "1.0.0"
    }


# Run server
if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server → http://{config.HOST}:{config.PORT}")
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info" if config.DEBUG else "warning",
        workers=1 if config.DEBUG else None,  # Let Docker/Gunicorn handle workers
    )