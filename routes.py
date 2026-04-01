import uuid
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from database import get_session, init_db
from models import Pattern, PatternOutcome, AgentBalance, Transaction
from config import settings
import json

app = FastAPI(title="DenialNet™", version="0.1.0")

# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class ResolutionInput(BaseModel):
    step: str
    order: int = 0

class PatternSubmit(BaseModel):
    carrier: str
    cpt_code: str
    icd10_code: Optional[str] = None
    specialty: str
    geography: Optional[str] = None
    denial_reason: str
    resolution_steps: list[str]
    attachments_required: Optional[list[str]] = None
    resubmission_format: Optional[str] = None
    contributor_id: str

class PatternSearchQuery(BaseModel):
    carrier: str
    cpt_code: str
    icd10_code: Optional[str] = None
    denial_reason: Optional[str] = None
    specialty: Optional[str] = None
    agent_id: str
    carrier: str
    cpt_code: str
    icd10_code: Optional[str] = None
    denial_reason: Optional[str] = None
    specialty: Optional[str] = None

class PatternResponse(BaseModel):
    pattern_id: str
    carrier: str
    cpt_code: str
    icd10_code: Optional[str]
    specialty: str
    geography: Optional[str]
    denial_reason: str
    resolution_steps: list
    attachments_required: Optional[list]
    resubmission_format: Optional[str]
    success_rate: float
    sample_size: int
    contributor_id: str
    created_at: str

class PatternPreview(BaseModel):
    carrier: str
    cpt_code: str
    success_rate: float
    sample_size: int
    match_level: str  # exact | partial | low

class OutcomeSubmit(BaseModel):
    outcome: str  # approved | denied | partial
    submitted_by: str
    notes: Optional[str] = None

class CreditTopup(BaseModel):
    agent_id: str
    stripe_token: str  # payment method token

# ── Dependency ────────────────────────────────────────────────────────────────

def db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "DenialNet™", "version": "0.1.0"}


@app.post("/patterns")
def submit_pattern(data: PatternSubmit, session: Session = Depends(db)):
    """Submit a new denial resolution pattern. Contributor earns on queries."""
    pattern = Pattern(
        carrier=data.carrier,
        cpt_code=data.cpt_code,
        icd10_code=data.icd10_code,
        specialty=data.specialty,
        geography=data.geography,
        denial_reason=data.denial_reason,
        resolution_steps=data.resolution_steps,
        attachments_required=data.attachments_required,
        resubmission_format=data.resubmission_format,
        success_rate=1.0,  # starts at 1.0, degrades with failures
        sample_size=1,
        contributor_id=data.contributor_id,
    )
    session.add(pattern)

    # Credit contributor with submission bonus
    ensure_balance(session, data.contributor_id)
    bal = session.query(AgentBalance).filter_by(agent_id=data.contributor_id).first()
    bal.balance_cents += 25  # $0.25 per submission bonus

    # Log transaction
    session.add(Transaction(
        agent_id=data.contributor_id,
        tx_type="pattern_submit",
        amount_cents=25,
        pattern_id=pattern.id,
        description="Pattern submission bonus"
    ))

    session.commit()
    return {
        "ok": True,
        "pattern_id": str(pattern.id),
        "submission_bonus_cents": 25,
        "message": "Pattern submitted. You'll earn when agents query it."
    }


@app.post("/patterns/search")
def query_patterns(
    data: PatternSearchQuery,
    session: Session = Depends(db)
):
    """Query denial patterns. Costs credits. Returns full resolution if unlocked."""
    # Check balance
    ensure_balance(session, data.agent_id)
    bal = session.query(AgentBalance).filter_by(agent_id=data.agent_id).first()
    if bal.balance_cents < settings.QUERY_COST_CENTS:
        raise HTTPException(402, f"Insufficient credits. Need {settings.QUERY_COST_CENTS}¢, have {bal.balance_cents}¢")

    # Build query
    q = session.query(Pattern).filter(
        Pattern.is_active == True,
        Pattern.carrier == data.carrier,
        Pattern.cpt_code == data.cpt_code,
    )
    if data.icd10_code:
        q = q.filter(Pattern.icd10_code == data.icd10_code)
    if data.specialty:
        q = q.filter(Pattern.specialty == data.specialty)

    # Rank by success rate + sample size
    results = q.order_by(desc(Pattern.success_rate), desc(Pattern.sample_size)).limit(5).all()

    if not results:
        return {
            "patterns": [],
            "total": 0,
            "cost_cents": 0,
            "balance_remaining_cents": bal.balance_cents,
            "message": "No patterns found for this combination. Submit one!"
        }

    # Deduct cost
    bal.balance_cents -= settings.QUERY_COST_CENTS

    # Log transaction
    session.add(Transaction(
        agent_id=data.agent_id,
        tx_type="query_unlock",
        amount_cents=-settings.QUERY_COST_CENTS,
        description=f"Query: {data.carrier}/{data.cpt_code}"
    ))

    # Pay contributor (proportional to their share of best result)
    top = results[0]
    contributor_pay = int(settings.QUERY_COST_CENTS * settings.CONTRIBUTOR_SPLIT)
    ensure_balance(session, top.contributor_id)
    contrib_bal = session.query(AgentBalance).filter_by(agent_id=top.contributor_id).first()
    contrib_bal.balance_cents += contributor_pay
    session.add(Transaction(
        agent_id=top.contributor_id,
        tx_type="pattern_query_earning",
        amount_cents=contributor_pay,
        pattern_id=top.id,
        description=f"Query payment from {data.agent_id}"
    ))

    session.commit()

    return {
        "patterns": [
            {
                "pattern_id": str(p.id),
                "carrier": p.carrier,
                "cpt_code": p.cpt_code,
                "icd10_code": p.icd10_code,
                "specialty": p.specialty,
                "geography": p.geography,
                "denial_reason": p.denial_reason,
                "resolution_steps": p.resolution_steps,
                "attachments_required": p.attachments_required,
                "resubmission_format": p.resubmission_format,
                "success_rate": round(p.success_rate, 3),
                "sample_size": p.sample_size,
                "contributor_id": p.contributor_id,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "match_level": _match_level(p, data.carrier, data.cpt_code, data.icd10_code),
            }
            for p in results
        ],
        "total": len(results),
        "cost_cents": settings.QUERY_COST_CENTS,
        "balance_remaining_cents": bal.balance_cents,
        "contributor_paid_cents": contributor_pay,
    }


@app.get("/patterns/{pattern_id}")
def get_pattern(pattern_id: str, session: Session = Depends(db)):
    """Get a specific pattern by ID."""
    import uuid as uuid_lib
    try:
        pid = uuid_lib.UUID(pattern_id)
    except ValueError:
        raise HTTPException(400, "Invalid pattern_id format")
    p = session.query(Pattern).filter_by(id=pid).first()
    if not p:
        raise HTTPException(404, "Pattern not found")
    return {
        "pattern_id": str(p.id),
        "carrier": p.carrier,
        "cpt_code": p.cpt_code,
        "icd10_code": p.icd10_code,
        "specialty": p.specialty,
        "denial_reason": p.denial_reason,
        "resolution_steps": p.resolution_steps,
        "attachments_required": p.attachments_required,
        "resubmission_format": p.resubmission_format,
        "success_rate": round(p.success_rate, 3),
        "sample_size": p.sample_size,
        "contributor_id": p.contributor_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@app.post("/patterns/{pattern_id}/outcome")
def submit_outcome(
    pattern_id: str,
    data: OutcomeSubmit,
    session: Session = Depends(db)
):
    """Log outcome of using a pattern. Updates success_rate."""
    import uuid as uuid_lib
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

    # Update success rate (exponential moving average)
    new_rate = 1.0 if data.outcome == "approved" else (0.5 if data.outcome == "partial" else 0.0)
    old_rate = p.success_rate
    n = p.sample_size
    p.success_rate = (old_rate * n + new_rate) / (n + 1)
    p.sample_size = n + 1

    # Deactivate if sample_size < MIN
    if p.sample_size < settings.MIN_SAMPLE_SIZE and p.success_rate < 0.3:
        p.is_active = False

    session.commit()
    return {
        "ok": True,
        "pattern_id": str(p.id),
        "new_success_rate": round(p.success_rate, 3),
        "new_sample_size": p.sample_size,
        "is_active": p.is_active,
    }


@app.get("/credits/{agent_id}")
def get_credits(agent_id: str, session: Session = Depends(db)):
    """Get agent credit balance."""
    ensure_balance(session, agent_id)
    bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
    return {
        "agent_id": agent_id,
        "balance_cents": bal.balance_cents,
        "balance_usd": round(bal.balance_cents / 100, 2),
    }


@app.get("/agents/{agent_id}/transactions")
def get_transactions(agent_id: str, limit: int = 20, session: Session = Depends(db)):
    """Get transaction history for an agent."""
    txs = session.query(Transaction).filter_by(agent_id=agent_id).order_by(desc(Transaction.created_at)).limit(limit).all()
    return {
        "agent_id": agent_id,
        "transactions": [
            {
                "id": str(t.id),
                "type": t.tx_type,
                "amount_cents": t.amount_cents,
                "pattern_id": str(t.pattern_id) if t.pattern_id else None,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in txs
        ]
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def ensure_balance(session, agent_id: str):
    bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
    if not bal:
        bal = AgentBalance(agent_id=agent_id, balance_cents=0)
        session.add(bal)
        session.commit()


def _match_level(p: Pattern, carrier: str, cpt_code: str, icd10_code: Optional[str]) -> str:
    if p.carrier == carrier and p.cpt_code == cpt_code and (not icd10_code or p.icd10_code == icd10_code):
        return "exact"
    elif p.carrier == carrier and p.cpt_code == cpt_code:
        return "partial"
    return "low"


# ── App startup ──────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()
