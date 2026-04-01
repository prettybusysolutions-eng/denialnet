from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, ForeignKey, CheckConstraint, DateTime as SAType, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Pattern(Base):
    __tablename__ = "patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrier = Column(String(100), nullable=False, index=True)
    cpt_code = Column(String(20), nullable=False, index=True)
    icd10_code = Column(String(20), index=True)
    specialty = Column(String(50), nullable=False, index=True)
    geography = Column(String(10))
    denial_reason = Column(String(255), nullable=False)
    resolution_steps = Column(JSON, nullable=False)
    attachments_required = Column(JSON)
    resubmission_format = Column(String(50))
    success_rate = Column(Float, nullable=False, default=0.5)
    sample_size = Column(Integer, nullable=False, default=1)
    contributor_id = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(SAType(timezone=True), server_default=func.now())
    updated_at = Column(SAType(timezone=True), server_default=func.now(), onupdate=func.now())

    outcomes = relationship("PatternOutcome", back_populates="pattern")

    __table_args__ = (
        CheckConstraint('success_rate >= 0 AND success_rate <= 1', name='valid_success_rate'),
        CheckConstraint('sample_size >= 1', name='valid_sample_size'),
    )


class PatternOutcome(Base):
    __tablename__ = "pattern_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("patterns.id"), nullable=False)
    outcome = Column(String(20), nullable=False)  # approved, denied, partial
    submitted_by = Column(String(100), nullable=False)
    notes = Column(Text)
    created_at = Column(SAType(timezone=True), server_default=func.now())

    pattern = relationship("Pattern", back_populates="outcomes")


class AgentBalance(Base):
    __tablename__ = "agent_balances"

    agent_id = Column(String(100), primary_key=True)
    balance_cents = Column(Integer, nullable=False, default=0)
    created_at = Column(SAType(timezone=True), server_default=func.now())
    updated_at = Column(SAType(timezone=True), server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), nullable=False, index=True)
    tx_type = Column(String(30), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    pattern_id = Column(UUID(as_uuid=True), ForeignKey("patterns.id"))
    description = Column(Text)
    created_at = Column(SAType(timezone=True), server_default=func.now())


class RateLimit(Base):
    """Per-agent, per-endpoint rate limit tracking."""
    __tablename__ = "rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), nullable=False)
    endpoint = Column(String(50), nullable=False)
    window_start = Column(SAType(timezone=True), server_default=func.now())
    request_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index('idx_rate_agent_endpoint', 'agent_id', 'endpoint'),
    )


class StripeCustomer(Base):
    __tablename__ = "stripe_customers"

    agent_id = Column(String(100), primary_key=True)
    stripe_customer_id = Column(String(100), nullable=False)
    created_at = Column(SAType(timezone=True), server_default=func.now())
