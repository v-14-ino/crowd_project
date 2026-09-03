from .auth import router as auth_router
from .database import router as database_router
from .evidence import router as evidence_router
from .incidents import router as incidents_router
from .reports import router as reports_router

__all__ = ["auth_router", "database_router", "evidence_router", "incidents_router", "reports_router"]

