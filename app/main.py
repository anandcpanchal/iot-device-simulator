from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.database import init_db
from app.api import devices
from app.engine import engine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Database...")
    await init_db()
    logger.info("Starting Simulation Engine...")
    await engine.start()
    yield
    # Shutdown
    logger.info("Stopping Simulation Engine...")
    await engine.stop()

app = FastAPI(lifespan=lifespan)

# Mount API routes
app.include_router(devices.router, prefix="/api")

# Mount Static Files (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
