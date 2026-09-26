import os
import sys
import types
import time
import logging

# Ensure the parent directory is in sys.path so 'backend.xxx' imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# If 'backend' is not in parent directory (e.g. in Vercel serverless root), alias current dir as 'backend'
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    backend_pkg.__path__ = [current_dir]
    sys.modules["backend"] = backend_pkg

from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.config import settings
from backend.database import init_db
from backend.utils.response import api_response

# 1. Create logs & upload directories if filesystem is writable
try:
    os.makedirs("logs", exist_ok=True)
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
except Exception:
    pass

# 2. Configure Logging
logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()

try:
    if os.path.exists("logs") and os.access("logs", os.W_OK):
        access_handler = RotatingFileHandler("logs/access.log", maxBytes=10*1024*1024, backupCount=5)
        access_handler.setLevel(logging.INFO)
        access_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(access_handler)

        error_handler = RotatingFileHandler("logs/errors.log", maxBytes=10*1024*1024, backupCount=5)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'))
        root_logger.addHandler(error_handler)
except Exception:
    pass

logger = logging.getLogger("app")

# 3. Create FastAPI app
app = FastAPI(
    title="NB BEADS STUDIO E-Commerce Backend",
    description="Production-Ready FastAPI + MongoDB Atlas Backend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 4. CORS Middleware
raw_origins = getattr(settings, "CORS_ORIGINS", "*") or "*"
if raw_origins.strip() == "*":
    cors_origins = ["*"]
    cors_regex = r"^https?://.*"
else:
    cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    cors_regex = None

default_dev_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

all_origins = list(set(default_dev_origins + (cors_origins if "*" not in cors_origins else [])))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in cors_origins else all_origins,
    allow_origin_regex=cors_regex if cors_regex else r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 5. Database Initializer & Request Logging Middleware
_db_initialized = False

@app.middleware("http")
async def app_middleware(request: Request, call_next):
    global _db_initialized
    if not _db_initialized:
        try:
            await init_db()
            _db_initialized = True
        except Exception as e:
            logger.error(f"Error initializing DB in middleware: {e}")

    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Log access details
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"{client_ip} - \"{request.method} {request.url.path}\" {response.status_code} - {process_time:.2f}ms")
    return response

# 6. Database Initialization on Startup (for uvicorn servers)
@app.on_event("startup")
async def on_startup():
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

# 7. Custom Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail} on path {request.url.path}")
    return api_response(
        success=False,
        message=exc.detail,
        status_code=exc.status_code
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation Error on path {request.url.path}: {exc.errors()}")
    return api_response(
        success=False,
        message="Request validation failed",
        errors=exc.errors(),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal Server Error on path {request.url.path}: {exc}", exc_info=True)
    return api_response(
        success=False,
        message="An unexpected server error occurred",
        errors=str(exc),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

# 8. Mount static files directory if available
if os.path.exists(settings.STATIC_DIR):
    app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

# 9. Register Routers
# Import routers inside app to avoid circular imports
from backend.routes.auth import router as auth_router
from backend.routes.products import router as products_router
from backend.routes.categories import router as categories_router
from backend.routes.cart import router as cart_router
from backend.routes.wishlist import router as wishlist_router
from backend.routes.orders import router as orders_router
from backend.routes.upload import router as upload_router
from backend.routes.admin import router as admin_router
from backend.routes.admin_api import router as admin_api_router
from backend.routes.settings import router as settings_router

app.include_router(auth_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(cart_router, prefix="/api")
app.include_router(wishlist_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(admin_api_router, prefix="/api")
app.include_router(settings_router, prefix="/api")

# Serve the legacy Admin HTML Jinja2 routes as fallback
app.include_router(admin_router)

# Redirect root path to API docs or dashboard
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/docs") if False else JSONResponse(content={"message": "NB BEADS STUDIO E-Commerce Backend is Running. Go to /docs for API documentation or /admin/login for dashboard."})
