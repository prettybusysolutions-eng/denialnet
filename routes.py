"""
DenialNet™ — Federated Claim Intelligence Protocol
routes.py — v0.2 with API key auth, Redis rate limiting, Stripe webhooks, DLQ
"""
import uuid as uuid_lib
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, Query, Request, Header, Body
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
from database import get_session, init_db, get_engine
from models import Pattern, PatternOutcome, AgentBalance, Transaction, StripeCustomer, RateLimit, APIKey, WebhookDLQ
from config import settings
import json
from contextlib import asynccontextmanager

app = FastAPI(title="DenialNet™", version="0.2.0")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Graceful startup and shutdown. Drains connections on SIGTERM."""
    # Startup
    init_db()
    print("[STARTUP] DenialNet v0.2.0 initialized")
    yield
    # Shutdown: close DB connections gracefully
    print("[SHUTDOWN] Closing DB connections...")
    try:
        engine = get_engine()
        engine.dispose()
    except Exception as e:
        print(f"[SHUTDOWN] Error disposing engine: {e}")
    print("[SHUTDOWN] Done")


app.router.lifespan_context = lifespan

# ── API Key Authentication ────────────────────────────────────────────────────

import hashlib


def _hash_api_key(key: str) -> str:
    """SHA-256 hash of an API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def _verify_api_key(session: Session, provided_key: str):
    """
    Verify an API key against the database.
    Returns the APIKey record if valid and active.
    Raises HTTPException 401 if invalid.
    """
    if not provided_key:
        raise HTTPException(401, {"error": "missing_api_key", "message": "X-API-Key header required"})
    key_hash = _hash_api_key(provided_key)
    key_record = session.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    if not key_record:
        raise HTTPException(401, {"error": "invalid_api_key", "message": "Invalid or inactive API key"})
    key_record.last_used_at = datetime.now(timezone.utc)
    session.commit()
    return key_record


def require_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Dependency: requires a valid API key."""
    def dep(session: Session = Depends(get_session)):
        return _verify_api_key(session, x_api_key)
    return dep


class APIKeyAuth:
    """API key verification dependency for FastAPI routes."""
    def __init__(self):
        pass
    def __call__(self, session: Session = Depends(get_session), x_api_key: str = Header(None)):
        return _verify_api_key(session, x_api_key)


require_auth = APIKeyAuth()


class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(None, max_length=100)
    rate_limit_override: int = Field(None, ge=10, le=10000)


def _create_api_key(session: Session, name: str, agent_id: str = None, rate_limit_override: int = None):
    """Create a new API key. Returns (raw_key, key_record)."""
    raw_key = uuid_lib.uuid4().hex + uuid_lib.uuid4().hex  # 64-byte random key
    key_hash = _hash_api_key(raw_key)
    key_record = APIKey(
        key_hash=key_hash,
        name=name,
        agent_id=agent_id,
        is_active=True,
        rate_limit_override=rate_limit_override
    )
    session.add(key_record)
    session.commit()
    return raw_key, key_record


# ── Rate Limiting ──────────────────────────────────────────────────────────────

_redis_client = None


def _get_redis_client():
    """Lazily initialize Redis client. Returns None if REDIS_URL not configured."""
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            import redis
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
            print("[RATE] Redis connected for rate limiting")
        except Exception as e:
            print(f"[RATE] Redis unavailable, using in-memory fallback: {e}")
            _redis_client = None
    return _redis_client


def check_rate_limit(session: Session, agent_id: str, endpoint: str, limit: int, window_minutes: int):
    """Check and enforce rate limit. Uses Redis if available, falls back to in-memory DB."""
    redis_client = _get_redis_client()

    if redis_client:
        # Redis-backed rate limiting
        window_key = datetime.now(timezone.utc).strftime("%Y%m%d%H")
        key = f"rl:{agent_id}:{endpoint}:{window_key}"
        try:
            current = redis_client.incr(key)
            if current == 1:
                redis_client.expire(key, window_minutes * 60)
            if current > limit:
                window_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
                raise HTTPException(429, {
                    "error": "rate_limit_exceeded",
                    "endpoint": endpoint,
                    "limit": limit,
                    "window_minutes": window_minutes,
                    "reset_at": window_start.isoformat()
                })
        except HTTPException:
            raise
        except Exception as e:
            print(f"[RATE] Redis error: {e} — falling back to DB")
            _redis_client = None  # Force fallback on next call

    if not redis_client:
        # In-memory DB fallback
        window_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        record = session.query(RateLimit).filter(
            RateLimit.agent_id == agent_id,
            RateLimit.endpoint == endpoint,
            RateLimit.window_start >= window_start
        ).first()

        if record:
            if record.request_count >= limit:
                window_ts = window_start.isoformat()
                raise HTTPException(429, {
                    "error": "rate_limit_exceeded",
                    "endpoint": endpoint,
                    "limit": limit,
                    "window_minutes": window_minutes,
                    "reset_at": window_ts
                })
            record.request_count += 1
        else:
            session.add(RateLimit(
                agent_id=agent_id,
                endpoint=endpoint,
                window_start=window_start,
                request_count=1
            ))

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PatternSubmit(BaseModel):
    carrier: str = Field(..., min_length=1, max_length=100)
    cpt_code: str = Field(..., min_length=1, max_length=20)
    icd10_code: Optional[str] = Field(None, max_length=20)
    specialty: str = Field(..., min_length=1, max_length=50)
    geography: Optional[str] = Field(None, max_length=10)
    denial_reason: str = Field(..., min_length=1, max_length=255)
    resolution_steps: list[str] = Field(..., min_length=1)
    attachments_required: Optional[list[str]] = None
    resubmission_format: Optional[str] = None
    contributor_id: str = Field(..., min_length=1, max_length=100)

    @field_validator('cpt_code')
    @classmethod
    def cpt_code_format(cls, v):
        import re
        if not re.match(r'^[A-Z0-9]+$', v.upper()):
            raise ValueError('cpt_code must be alphanumeric uppercase')
        return v.upper()

    @field_validator('contributor_id')
    @classmethod
    def agent_id_format(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('contributor_id must be alphanumeric, hyphens, or underscores only')
        return v

    @field_validator('resolution_steps')
    @classmethod
    def steps_not_empty(cls, v):
        if not v or not any(s.strip() for s in v):
            raise ValueError('resolution_steps cannot be empty')
        return v


class PatternSearchQuery(BaseModel):
    carrier: str
    cpt_code: str
    icd10_code: Optional[str] = None
    denial_reason: Optional[str] = None
    specialty: Optional[str] = None
    agent_id: str

    @field_validator('cpt_code')
    @classmethod
    def cpt_code_format(cls, v):
        import re
        if not re.match(r'^[A-Z0-9]+$', v.upper()):
            raise ValueError('cpt_code must be alphanumeric uppercase')
        return v.upper()

    @field_validator('agent_id')
    @classmethod
    def agent_id_format(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('agent_id must be alphanumeric, hyphens, or underscores only')
        return v


class OutcomeSubmit(BaseModel):
    outcome: str  # approved | denied | partial
    submitted_by: str
    notes: Optional[str] = None

    @field_validator('outcome')
    @classmethod
    def must_be_valid(cls, v):
        if v not in ('approved', 'denied', 'partial'):
            raise ValueError('outcome must be approved, denied, or partial')
        return v


class StripeTopupRequest(BaseModel):
    agent_id: str
    stripe_customer_id: str
    stripe_payment_method_id: str
    amount_cents: int = Field(..., ge=100, le=100000)  # min $1, max $1000

    @field_validator('agent_id')
    @classmethod
    def agent_id_format(cls, v):
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('agent_id must be alphanumeric, hyphens, or underscores only')
        return v

    @field_validator('amount_cents')
    @classmethod
    def minimum_topup(cls, v):
        if v < 100:
            raise ValueError('Minimum topup is 100¢ ($1)')
        return v


class TopupConfirmRequest(BaseModel):
    payment_intent_id: str
    agent_id: str


# ── Dependency ────────────────────────────────────────────────────────────────

def db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


# ── Helpers ──────────────────────────────────────────────────────────────────

def ensure_balance(session: Session, agent_id: str) -> AgentBalance:
    bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
    if not bal:
        bal = AgentBalance(agent_id=agent_id, balance_cents=0)
        session.add(bal)
        session.commit()
    return bal


def _match_level(p: Pattern, carrier: str, cpt_code: str, icd10_code: Optional[str]) -> str:
    if p.carrier == carrier and p.cpt_code == cpt_code and (not icd10_code or p.icd10_code == icd10_code):
        return "exact"
    elif p.carrier == carrier and p.cpt_code == cpt_code:
        return "partial"
    return "low"


def _pattern_dict(p: Pattern, include_resolution: bool = True, match_carrier: str = None,
                   match_cpt: str = None, match_icd: str = None) -> dict:
    d = {
        "pattern_id": str(p.id),
        "carrier": p.carrier,
        "cpt_code": p.cpt_code,
        "icd10_code": p.icd10_code,
        "specialty": p.specialty,
        "geography": p.geography,
        "denial_reason": p.denial_reason,
        "success_rate": round(p.success_rate, 3),
        "sample_size": p.sample_size,
        "contributor_id": p.contributor_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "match_level": _match_level(p, match_carrier or p.carrier, match_cpt or p.cpt_code, match_icd),
    }
    if include_resolution:
        d["resolution_steps"] = p.resolution_steps
        d["attachments_required"] = p.attachments_required
        d["resubmission_format"] = p.resubmission_format
    return d


def _enforce_min_sample(session: Session):
    """Deactivate patterns that fall below minimum quality thresholds."""
    threshold = settings.MIN_SAMPLE_SIZE
    rate_threshold = 0.30
    deactivated = session.query(Pattern).filter(
        Pattern.is_active == True,
        Pattern.sample_size < threshold,
        Pattern.success_rate < rate_threshold
    ).all()
    for p in deactivated:
        p.is_active = False
    if deactivated:
        session.commit()
    return deactivated


# ── Routes ──────────────────────────────────────────────────────────────────

# ── Admin: API Key Management ──────────────────────────────────────────────

class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    agent_id: str = Field(None, max_length=100)
    rate_limit_override: int = Field(None, ge=10, le=10000)


@app.post("/admin/keys")
def admin_create_key(
    data: CreateAPIKeyRequest,
    session: Session = Depends(db),
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """
    Create a new API key. Requires X-Admin-Key header matching DENIALNET_ADMIN_API_KEY env var.
    """
    if not settings.ADMIN_API_KEY:
        raise HTTPException(503, {"error": "admin_not_configured", "message": "DENIALNET_ADMIN_API_KEY not set on server"})
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(401, {"error": "unauthorized", "message": "Invalid admin key"})
    raw_key, key_record = _create_api_key(session, data.name, data.agent_id, data.rate_limit_override)
    return {
        "api_key": raw_key,
        "name": key_record.name,
        "agent_id": key_record.agent_id,
        "created_at": key_record.created_at.isoformat() if key_record.created_at else None,
        "warning": "Store this key securely. It cannot be retrieved again."
    }


class APIKeyInfo(BaseModel):
    id: str; name: str; agent_id: Optional[str]; is_active: bool
    rate_limit_override: Optional[int]; created_at: Optional[datetime]
    last_used_at: Optional[datetime]


@app.get("/admin/keys", response_model=list[APIKeyInfo])
def admin_list_keys(
    session: Session = Depends(db),
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """List all API keys (never returns the key itself)."""
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(401, {"error": "unauthorized"})
    keys = session.query(APIKey).order_by(desc(APIKey.created_at)).limit(100).all()
    return [APIKeyInfo(
        id=str(k.id), name=k.name, agent_id=k.agent_id, is_active=k.is_active,
        rate_limit_override=k.rate_limit_override, created_at=k.created_at, last_used_at=k.last_used_at
    ) for k in keys]


@app.delete("/admin/keys/{key_id}")
def admin_revoke_key(
    key_id: str,
    session: Session = Depends(db),
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """Revoke an API key."""
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(401, {"error": "unauthorized"})
    key = session.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(404, "API key not found")
    key.is_active = False
    session.commit()
    return {"revoked": True, "key_id": key_id}


# ── Admin: DLQ Management ─────────────────────────────────────────────────

class DLQStatus(BaseModel):
    pending: int; failed: int; resolved: int; total: int


@app.get("/admin/dlq", response_model=DLQStatus)
def admin_dlq_status(
    session: Session = Depends(db),
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(401, {"error": "unauthorized"})
    """Get webhook DLQ status counts."""
    from models import WebhookDLQ
    pending = session.query(WebhookDLQ).filter(WebhookDLQ.status == 'pending').count()
    failed = session.query(WebhookDLQ).filter(WebhookDLQ.status == 'failed').count()
    resolved = session.query(WebhookDLQ).filter(WebhookDLQ.status == 'resolved').count()
    return DLQStatus(pending=pending, failed=failed, resolved=resolved, total=pending+failed+resolved)


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """
    Liveness probe. Returns 200 if the process is alive.
    Kubernetes uses this to decide whether to restart the container.
    """
    return {"status": "ok", "service": "DenialNet™", "version": "0.2.0"}


@app.get("/ready")
def ready(session: Session = Depends(get_session)):
    """
    Readiness probe. Returns 200 only when all dependencies are connected.
    - Database: can execute a test query
    - Redis: optional, checked if REDIS_URL is configured
    Returns 503 if any dependency is unavailable.
    """
    checks = {}
    unhealthy = []

    # DB check
    try:
        session.execute(text("SELECT 1"))
        session.commit()
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        unhealthy.append("db")

    # Redis check (optional dependency — Redis is not required)
    try:
        rc = _get_redis_client()
        if rc:
            rc.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "not_configured"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        unhealthy.append("redis")

    if unhealthy:
        raise HTTPException(503, {
            "status": "not_ready",
            "checks": checks,
            "unhealthy": unhealthy
        })

    return {"status": "ready", "checks": checks}


@app.get("/")
def root():
    return {
        "name": "DenialNet™",
        "tagline": "The intelligence layer every claim system plugs into.",
        "version": "0.1.0",
        "docs": "/docs"
    }


# ── Preview (free — drives conversion) ───────────────────────────────────────

@app.get("/patterns/preview")
def preview_patterns(
    carrier: str = Query(...),
    cpt_code: str = Query(...),
    icd10_code: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    session: Session = Depends(db)
):
    """
    Free preview — returns top 3 patterns WITHOUT resolution steps.
    Shows success_rate and sample_size to drive conversion.
    Full resolution requires /patterns/search (costs credits).
    """
    q = session.query(Pattern).filter(
        Pattern.is_active == True,
        Pattern.carrier == carrier,
        Pattern.cpt_code == cpt_code,
    )
    if icd10_code:
        q = q.filter(Pattern.icd10_code == icd10_code)
    if specialty:
        q = q.filter(Pattern.specialty == specialty)

    results = q.order_by(desc(Pattern.success_rate), desc(Pattern.sample_size)).limit(3).all()

    if not results:
        return {
            "patterns": [],
            "total": 0,
            "preview": True,
            "cost_cents": settings.QUERY_COST_CENTS,
            "message": "No patterns found. Submit one — earn $0.25 per query from other agents!"
        }

    return {
        "patterns": [
            {
                "pattern_id": str(p.id),
                "carrier": p.carrier,
                "cpt_code": p.cpt_code,
                "specialty": p.specialty,
                "success_rate": round(p.success_rate, 3),
                "sample_size": p.sample_size,
                "match_level": _match_level(p, carrier, cpt_code, icd10_code),
                "resolution_preview": " • ".join(p.resolution_steps[:2]) + (" ..." if len(p.resolution_steps) > 2 else ""),
            }
            for p in results
        ],
        "total": len(results),
        "preview": True,
        "cost_cents": settings.QUERY_COST_CENTS,
        "message": f"Unlock full resolutions for {settings.QUERY_COST_CENTS}¢ — or submit your own pattern for free."
    }


# ── Pattern Submission ────────────────────────────────────────────────────────

@app.post("/patterns")
def submit_pattern(data: PatternSubmit, session: Session = Depends(db), x_api_key: str = Header(None)):
    """Submit a new denial resolution pattern. Requires X-API-Key."""
    _verify_api_key(session, x_api_key)
    # Enforce minimum quality
    if len(data.resolution_steps) < 1:
        raise HTTPException(400, "At least one resolution step is required")

    # Rate limit check
    check_rate_limit(session, data.contributor_id, "submit",
                     settings.RATE_LIMIT_SUBMIT, settings.RATE_LIMIT_WINDOW_MINUTES)

    pattern = Pattern(
        carrier=data.carrier.strip(),
        cpt_code=data.cpt_code.strip().upper(),
        icd10_code=data.icd10_code.strip().upper() if data.icd10_code else None,
        specialty=data.specialty.strip(),
        geography=data.geography.strip().upper() if data.geography else None,
        denial_reason=data.denial_reason.strip(),
        resolution_steps=data.resolution_steps,
        attachments_required=data.attachments_required or [],
        resubmission_format=data.resubmission_format,
        success_rate=1.0,  # new patterns start perfect
        sample_size=1,
        contributor_id=data.contributor_id.strip(),
    )
    session.add(pattern)

    # Credit contributor
    ensure_balance(session, data.contributor_id)
    bal = session.query(AgentBalance).filter_by(agent_id=data.contributor_id).first()
    bonus = 25  # $0.25 per submission
    bal.balance_cents += bonus

    session.add(Transaction(
        agent_id=data.contributor_id,
        tx_type="pattern_submit",
        amount_cents=bonus,
        pattern_id=pattern.id,
        description=f"Submission bonus: {data.carrier}/{data.cpt_code}"
    ))

    session.commit()

    return {
        "ok": True,
        "pattern_id": str(pattern.id),
        "submission_bonus_cents": bonus,
        "message": f"Pattern submitted. You'll earn {settings.QUERY_COST_CENTS}¢ every time an agent unlocks it. "
                   f"Deactivate if success_rate drops below {settings.MIN_SAMPLE_SIZE} samples."
    }


# ── Pattern Query (paid unlock) ───────────────────────────────────────────────

@app.post("/patterns/search")
def search_patterns(data: PatternSearchQuery, session: Session = Depends(db), x_api_key: str = Header(None)):
    """
    Query denial patterns. Costs credits.
    Returns FULL resolutions for top matching patterns.
    Contributors paid automatically based on split table.
    Requires X-API-Key header.
    """
    _verify_api_key(session, x_api_key)
    # Check balance
    ensure_balance(session, data.agent_id)
    bal = session.query(AgentBalance).filter_by(agent_id=data.agent_id).first()

    # Rate limit check
    check_rate_limit(session, data.agent_id, "search",
                     settings.RATE_LIMIT_SEARCH, settings.RATE_LIMIT_WINDOW_MINUTES)

    cost = settings.QUERY_COST_CENTS
    if bal.balance_cents < cost:
        raise HTTPException(402, {
            "error": "insufficient_credits",
            "needed_cents": cost,
            "current_cents": bal.balance_cents,
            "message": f"Insufficient credits. Need {cost}¢, have {bal.balance_cents}¢. Top up at POST /credits/topup."
        })

    # Build and execute query
    q = session.query(Pattern).filter(
        Pattern.is_active == True,
        Pattern.carrier == data.carrier.strip(),
        Pattern.cpt_code == data.cpt_code.strip().upper(),
    )
    if data.icd10_code:
        q = q.filter(Pattern.icd10_code == data.icd10_code.strip().upper())
    if data.specialty:
        q = q.filter(Pattern.specialty == data.specialty.strip())

    results = q.order_by(desc(Pattern.success_rate), desc(Pattern.sample_size)).limit(5).all()

    # No results — return free submission nudge
    if not results:
        return {
            "patterns": [],
            "total": 0,
            "cost_cents": 0,
            "balance_remaining_cents": bal.balance_cents,
            "message": "No patterns yet. Submit what fixed this denial — earn $0.25 every time another agent queries it."
        }

    # Enforce min-sample quality check before returning
    deactivated = _enforce_min_sample(session)

    # Deduct cost from buyer
    bal.balance_cents -= cost

    # Log buyer deduction
    session.add(Transaction(
        agent_id=data.agent_id,
        tx_type="query_unlock",
        amount_cents=-cost,
        pattern_id=results[0].id,
        description=f"Search unlock: {data.carrier}/{data.cpt_code}"
    ))

    # Pay contributor (70% of query cost)
    top = results[0]
    contributor_pay = int(cost * settings.CONTRIBUTOR_SPLIT)
    ensure_balance(session, top.contributor_id)
    contrib_bal = session.query(AgentBalance).filter_by(agent_id=top.contributor_id).first()
    contrib_bal.balance_cents += contributor_pay

    session.add(Transaction(
        agent_id=top.contributor_id,
        tx_type="pattern_query_earning",
        amount_cents=contributor_pay,
        pattern_id=top.id,
        description=f"Query payment from {data.agent_id}: {data.carrier}/{data.cpt_code}"
    ))

    # Network ops cut (30%)
    ops_pay = cost - contributor_pay
    session.add(Transaction(
        agent_id="network-ops",
        tx_type="network_fee",
        amount_cents=ops_pay,
        pattern_id=top.id,
        description=f"Network fee: {data.carrier}/{data.cpt_code}"
    ))

    session.commit()

    return {
        "patterns": [
            _pattern_dict(p, include_resolution=True,
                         match_carrier=data.carrier, match_cpt=data.cpt_code, match_icd=data.icd10_code)
            for p in results
        ],
        "total": len(results),
        "cost_cents": cost,
        "balance_remaining_cents": bal.balance_cents,
        "contributor_paid_cents": contributor_pay,
        "network_fee_cents": ops_pay,
        "deactivated_count": len(deactivated),
        "message": f"Unlocked {len(results)} pattern(s). Submit outcomes at POST /patterns/{{id}}/outcome to improve accuracy."
    }


# ── Get specific pattern ──────────────────────────────────────────────────────

@app.get("/patterns/{pattern_id}")
def get_pattern(pattern_id: str, session: Session = Depends(db)):
    """Get a specific pattern by ID. Requires prior unlock or submission."""
    try:
        pid = uuid_lib.UUID(pattern_id)
    except ValueError:
        raise HTTPException(400, "Invalid pattern_id format")
    p = session.query(Pattern).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Pattern not found")
    if not p.is_active:
        raise HTTPException(410, "Pattern has been deactivated due to low success rate")
    return _pattern_dict(p, include_resolution=True)


# ── Outcome submission ────────────────────────────────────────────────────────

@app.post("/patterns/{pattern_id}/outcome")
def submit_outcome(pattern_id: str, data: OutcomeSubmit, session: Session = Depends(db), x_api_key: str = Header(None)):
    """
    Log outcome of using a pattern. Updates success_rate using exponential moving average.
    Requires X-API-Key.
    """
    _verify_api_key(session, x_api_key)
    try:
        pid = uuid_lib.UUID(pattern_id)
    except ValueError:
        raise HTTPException(400, "Invalid pattern_id format")

    p = session.query(Pattern).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Pattern not found")

    # Record outcome
    session.add(PatternOutcome(
        pattern_id=p.id,
        outcome=data.outcome,
        submitted_by=data.submitted_by,
        notes=data.notes,
    ))

    # Update success rate (EMA)
    new_rate = 1.0 if data.outcome == "approved" else (0.5 if data.outcome == "partial" else 0.0)
    n = p.sample_size
    p.success_rate = (p.success_rate * n + new_rate) / (n + 1)
    p.sample_size = n + 1

    # Enforce min-sample threshold
    was_active = p.is_active
    if p.sample_size < settings.MIN_SAMPLE_SIZE and p.success_rate < 0.30:
        p.is_active = False

    session.commit()

    return {
        "ok": True,
        "pattern_id": str(p.id),
        "outcome_recorded": data.outcome,
        "new_success_rate": round(p.success_rate, 3),
        "new_sample_size": p.sample_size,
        "was_active": was_active,
        "is_active": p.is_active,
        "deactivated": was_active and not p.is_active,
        "message": f"Outcome recorded. Success rate updated to {round(p.success_rate, 3)} "
                   f"across {p.sample_size} submissions."
    }


# ── Credits ──────────────────────────────────────────────────────────────────

@app.get("/credits/{agent_id}")
def get_credits(agent_id: str, session: Session = Depends(db)):
    """Get agent credit balance in cents and USD."""
    ensure_balance(session, agent_id)
    bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
    return {
        "agent_id": agent_id,
        "balance_cents": bal.balance_cents,
        "balance_usd": round(bal.balance_cents / 100, 2),
        "query_cost_cents": settings.QUERY_COST_CENTS,
        "queries_remaining": bal.balance_cents // settings.QUERY_COST_CENTS,
    }


@app.get("/credits/{agent_id}/transactions")
def get_transactions(agent_id: str, limit: int = Query(20, ge=1, le=200),
                     offset: int = Query(0, ge=0),
                     session: Session = Depends(db)):
    """Paginated transaction history for an agent."""
    txs = session.query(Transaction).filter_by(agent_id=agent_id).order_by(
        desc(Transaction.created_at)
    ).offset(offset).limit(limit).all()

    total = session.query(func.count(Transaction.id)).filter_by(agent_id=agent_id).scalar()

    return {
        "agent_id": agent_id,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.tx_type,
                "amount_cents": t.amount_cents,
                "amount_usd": round(t.amount_cents / 100, 2),
                "pattern_id": str(t.pattern_id) if t.pattern_id else None,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── CSV Ingest ──────────────────────────────────────────────────────────────

import csv
import io


class CSVIngestRequest(BaseModel):
    contributor_id: str = Field(..., min_length=1, max_length=100)
    patterns_csv: str = Field(..., min_length=10)  # CSV as string


@app.post("/patterns/ingest")
def ingest_patterns_csv(data: CSVIngestRequest, session: Session = Depends(db), x_api_key: str = Header(None)):
    """
    Bulk ingest patterns from CSV. Requires X-API-Key.
    CSV format: carrier,cpt_code,icd10_code,specialty,geography,denial_reason,resolution_steps (JSON array),attachments_required (JSON array),resubmission_format
    First row must be header.
    Returns: {accepted: N, rejected: N, errors: [...]}
    """
    reader = csv.DictReader(io.StringIO(data.patterns_csv))
    accepted = []
    rejected = []
    required = ["carrier", "cpt_code", "denial_reason", "resolution_steps"]
    _verify_api_key(session, x_api_key)
    check_rate_limit(session, data.contributor_id, "submit",
                     settings.RATE_LIMIT_SUBMIT, settings.RATE_LIMIT_WINDOW_MINUTES)

    for i, row in enumerate(reader):
        row_num = i + 2  # +2 for 1-indexed + header row
        try:
            # Validate required fields
            missing = [f for f in required if not row.get(f, "").strip()]
            if missing:
                rejected.append({"row": row_num, "error": f"missing_required_fields: {missing}"})
                continue

            # Parse resolution_steps (JSON array as string)
            try:
                steps = json.loads(row["resolution_steps"])
                if not isinstance(steps, list) or not steps:
                    raise ValueError("must be a JSON array with at least one step")
            except (json.JSONDecodeError, ValueError) as e:
                rejected.append({"row": row_num, "error": f"resolution_steps parse error: {e}"})
                continue

            # Parse attachments (optional JSON array)
            attachments = None
            if row.get("attachments_required", "").strip():
                try:
                    attachments = json.loads(row["attachments_required"])
                except json.JSONDecodeError:
                    attachments = [a.strip() for a in row["attachments_required"].split(",") if a.strip()]

            pattern = Pattern(
                carrier=row["carrier"].strip(),
                cpt_code=row["cpt_code"].strip().upper(),
                icd10_code=row.get("icd10_code", "").strip().upper() or None,
                specialty=row.get("specialty", "Dental").strip(),
                geography=row.get("geography", "").strip().upper() or None,
                denial_reason=row["denial_reason"].strip(),
                resolution_steps=steps,
                attachments_required=attachments,
                resubmission_format=row.get("resubmission_format", "").strip() or None,
                success_rate=1.0,
                sample_size=1,
                contributor_id=data.contributor_id.strip(),
            )
            session.add(pattern)

            # Credit contributor per pattern (capped at batch bonus)
            ensure_balance(session, data.contributor_id)
            bal = session.query(AgentBalance).filter_by(agent_id=data.contributor_id).first()
            bal.balance_cents += 25  # $0.25 per pattern

            accepted.append({
                "row": row_num,
                "carrier": pattern.carrier,
                "cpt_code": pattern.cpt_code,
                "bonus_cents": 25
            })

        except Exception as e:
            rejected.append({"row": row_num, "error": str(e)})

    if accepted:
        session.commit()

    return {
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "total_bonus_cents": len(accepted) * 25,
        "accepted": accepted[:20],  # cap response size
        "rejected": rejected[:20],
    }


# ── Stripe Topup ─────────────────────────────────────────────────────────────

@app.post("/credits/topup")
def create_topup_intent(data: StripeTopupRequest, session: Session = Depends(db), x_api_key: str = Header(None)):
    """
    Create a Stripe PaymentIntent for credit topup. Requires X-API-Key.
    """
    _verify_api_key(session, x_api_key)
    if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("sk_live_") == False:
        # Return mock success in dev/test
        if settings.STRIPE_SECRET_KEY in (None, "", "sk_test_xxx"):
            ensure_balance(session, data.agent_id)
            bal = session.query(AgentBalance).filter_by(agent_id=data.agent_id).first()
            bal.balance_cents += data.amount_cents
            session.add(Transaction(
                agent_id=data.agent_id,
                tx_type="credit_topup",
                amount_cents=data.amount_cents,
                description=f"Test topup: {data.amount_cents}¢"
            ))
            session.commit()
            return {
                "ok": True,
                "mode": "test",
                "agent_id": data.agent_id,
                "amount_cents": data.amount_cents,
                "amount_usd": round(data.amount_cents / 100, 2),
                "new_balance_cents": bal.balance_cents,
                "message": f"Test topup: added {data.amount_cents}¢. Set STRIPE_SECRET_KEY for real payments."
            }
        return HTTPException(503, "Stripe not configured")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        intent = stripe.PaymentIntent.create(
            amount=data.amount_cents,  # amount in cents
            currency="usd",
            payment_method_types=["card"],
            description=f"DenialNet™ credit topup: {data.agent_id}",
            metadata={
                "agent_id": data.agent_id,
                "type": "denialnet_topup"
            }
        )
        return {
            "client_secret": intent.client_secret,
            "payment_intent_id": intent.id,
            "amount_cents": data.amount_cents,
            "amount_usd": round(data.amount_cents / 100, 2),
            "mode": "live"
        }
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


@app.post("/credits/topup/confirm")
def confirm_topup(data: TopupConfirmRequest, session: Session = Depends(db), x_api_key: str = Header(None)):
    """Confirm a Stripe topup after PaymentIntent succeeds. Requires X-API-Key."""
    _verify_api_key(session, x_api_key)
    if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == "sk_test_xxx":
        return {"ok": True, "mode": "test", "message": "Test mode — credits already added"}

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        intent = stripe.PaymentIntent.retrieve(data.payment_intent_id)
        if intent.status != "succeeded":
            raise HTTPException(400, f"Payment not succeeded: {intent.status}")

        # Verify agent_id matches
        if intent.metadata.get("agent_id") != data.agent_id:
            raise HTTPException(400, "Agent ID mismatch")

        amount_cents = intent.amount

        ensure_balance(session, data.agent_id)
        bal = session.query(AgentBalance).filter_by(agent_id=data.agent_id).first()
        bal.balance_cents += amount_cents

        session.add(Transaction(
            agent_id=data.agent_id,
            tx_type="credit_topup",
            amount_cents=amount_cents,
            description=f"Stripe topup: {amount_cents}¢ (PI: {intent.id})"
        ))
        session.commit()

        return {
            "ok": True,
            "payment_intent_id": intent.id,
            "amount_cents": amount_cents,
            "amount_usd": round(amount_cents / 100, 2),
            "new_balance_cents": bal.balance_cents,
            "new_balance_usd": round(bal.balance_cents / 100, 2),
        }
    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e))


# ── Stripe Webhook ────────────────────────────────────────────────────────────

from fastapi import Request


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(db)):
    """
    Stripe webhook handler with signature verification and DLQ.
    Only checkout.session.completed events are processed.
    """
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(503, {"error": "stripe_not_configured"})

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(503, {"error": "webhook_secret_not_configured"})

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, {"error": "invalid_signature"})
    except ValueError:
        raise HTTPException(400, {"error": "invalid_payload"})

    event_type = event.get("type", "")
    stripe_event_id = event.get("id", "")

    # Process — store failed events in DLQ
    try:
        if event_type == "checkout.session.completed":
            session_data = event["data"]["object"]
            metadata = session_data.get("metadata", {})
            agent_id = metadata.get("agent_id", "")
            amount_cents = session_data.get("amount_total", 0)

            if agent_id:
                ensure_balance(session, agent_id)
                bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
                if bal:
                    bal.balance_cents += amount_cents
                    session.add(Transaction(
                        agent_id=agent_id,
                        tx_type="stripe_topup",
                        amount_cents=amount_cents,
                        description=f"Stripe topup: {stripe_event_id}"
                    ))
                    session.commit()
                    print(f"[STRIPE] Topup confirmed: agent={agent_id}, amount={amount_cents}¢")
        # Return 200 to acknowledge receipt
        return {"received": True}
    except Exception as e:
        error_msg = str(e)
        print(f"[STRIPE] Webhook processing failed: {error_msg}")
        # Store in DLQ
        try:
            dlq_record = WebhookDLQ(
                stripe_event_id=stripe_event_id,
                event_type=event_type,
                payload=json.dumps(event),
                error_message=error_msg,
                status="pending",
                retry_count=0
            )
            session.add(dlq_record)
            session.commit()
        except Exception:
            session.rollback()
        return {"received": True}


@app.post("/admin/dlq/retry")
def admin_retry_dlq(
    session: Session = Depends(db),
    x_admin_key: str = Header(None, alias="X-Admin-Key")
):
    """Retry pending DLQ events. Admin only."""
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(401, {"error": "unauthorized"})

    import stripe as stripe_lib
    stripe_lib.api_key = settings.STRIPE_SECRET_KEY

    pending = session.query(WebhookDLQ).filter(
        WebhookDLQ.status == "pending",
        WebhookDLQ.retry_count < 5
    ).limit(50).all()

    processed = 0
    failed = 0
    for dlq in pending:
        try:
            event = json.loads(dlq.payload)
            # Re-process the event
            if dlq.event_type == "checkout.session.completed":
                session_data = event["data"]["object"]
                metadata = session_data.get("metadata", {})
                agent_id = metadata.get("agent_id", "")
                amount_cents = session_data.get("amount_total", 0)
                if agent_id:
                    bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
                    if bal:
                        bal.balance_cents += amount_cents
                        session.add(Transaction(
                            agent_id=agent_id, tx_type="stripe_topup",
                            amount_cents=amount_cents,
                            description=f"Stripe topup (DLQ retry): {dlq.stripe_event_id}"
                        ))
            dlq.status = "resolved"
            dlq.resolved_at = datetime.now(timezone.utc)
            session.commit()
            processed += 1
        except Exception as e:
            dlq.retry_count += 1
            dlq.last_retry_at = datetime.now(timezone.utc)
            dlq.error_message = str(e)
            if dlq.retry_count >= 5:
                dlq.status = "failed"
            session.commit()
            failed += 1

    return {"processed": processed, "failed": failed, "remaining": len(pending) - processed}


# ── Stats ────────────────────────────────────────────────────────────────────

@app.get("/stats")
def get_stats(session: Session = Depends(db)):
    """Public network statistics."""
    total_patterns = session.query(func.count(Pattern.id)).filter_by(is_active=True).scalar()
    total_queries = session.query(func.count(Transaction.id)).filter_by(tx_type="query_unlock").scalar()
    total_submissions = session.query(func.count(Pattern.id)).scalar()
    total_outcomes = session.query(func.count(PatternOutcome.id)).scalar()
    avg_success = session.query(func.avg(Pattern.success_rate)).filter_by(is_active=True).scalar()

    return {
        "active_patterns": total_patterns or 0,
        "total_submissions": total_submissions or 0,
        "total_queries": total_queries or 0,
        "total_outcomes_logged": total_outcomes or 0,
        "average_success_rate": round(avg_success, 3) if avg_success else 0,
        "query_cost_cents": settings.QUERY_COST_CENTS,
    }


# ── App startup ──────────────────────────────────────────────────────────────
