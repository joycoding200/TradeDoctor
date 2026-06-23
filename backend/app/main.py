from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.database import engine, Base, SessionLocal
from app.api import api_router
from app.ratelimit import limiter

# Import all models so Base.metadata knows about them
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # NOTE: create_all is fine for development/testing. For production, use
    # Alembic migrations (alembic upgrade head) to manage schema changes
    # and avoid table drift. See docs/ for migration setup.
    Base.metadata.create_all(bind=engine)

    # Backfill: migrate existing single-file analyses to analysis_files table
    _backfill_analysis_files()

    yield


def _backfill_analysis_files():
    """Ensure legacy analyses are represented in the analysis_files join table."""
    db = SessionLocal()
    try:
        # Check if the analysis_files table exists (created by create_all)
        db.execute(text("SELECT 1 FROM analysis_files LIMIT 0"))
    except Exception:
        db.close()
        return  # table doesn't exist yet (first run before create_all?)

    try:
        result = db.execute(
            text(
                "INSERT INTO analysis_files (analysis_id, raw_file_id) "
                "SELECT id, raw_file_id FROM analyses "
                "WHERE raw_file_id IS NOT NULL "
                "AND (id, raw_file_id) NOT IN (SELECT analysis_id, raw_file_id FROM analysis_files) "
                "ON CONFLICT DO NOTHING"
            )
        )
        db.commit()
        if result.rowcount and result.rowcount > 0:
            import logging
            logging.getLogger(__name__).info(
                f"Backfilled {result.rowcount} analysis-file associations"
            )
    except Exception:
        db.rollback()
    finally:
        db.close()


app = FastAPI(title="TradingJournalAnalyzer API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
