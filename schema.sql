-- DenialNet™ Database Schema v0.1
-- PostgreSQL-compatible

-- Patterns table
CREATE TABLE IF NOT EXISTS patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    carrier VARCHAR(100) NOT NULL,
    cpt_code VARCHAR(20) NOT NULL,
    icd10_code VARCHAR(20),
    specialty VARCHAR(50) NOT NULL,
    geography VARCHAR(10),
    denial_reason VARCHAR(255) NOT NULL,
    resolution_steps JSONB NOT NULL,
    attachments_required JSONB,
    resubmission_format VARCHAR(50),
    success_rate REAL NOT NULL DEFAULT 0.5,
    sample_size INTEGER NOT NULL DEFAULT 1,
    contributor_id VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_patterns_carrier ON patterns(carrier);
CREATE INDEX idx_patterns_cpt ON patterns(cpt_code);
CREATE INDEX idx_patterns_icd10 ON patterns(icd10_code);
CREATE INDEX idx_patterns_specialty ON patterns(specialty);
CREATE INDEX idx_patterns_success_rate ON patterns(success_rate DESC);
CREATE INDEX idx_patterns_active ON patterns(is_active) WHERE is_active = TRUE;

-- Pattern outcomes (for success_rate tracking)
CREATE TABLE IF NOT EXISTS pattern_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_id UUID NOT NULL REFERENCES patterns(id),
    outcome VARCHAR(20) NOT NULL CHECK (outcome IN ('approved', 'denied', 'partial')),
    submitted_by VARCHAR(100) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outcomes_pattern ON pattern_outcomes(pattern_id);

-- Agent credit balances
CREATE TABLE IF NOT EXISTS agent_balances (
    agent_id VARCHAR(100) PRIMARY KEY,
    balance_cents INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Transaction ledger
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id VARCHAR(100) NOT NULL,
    tx_type VARCHAR(30) NOT NULL CHECK (tx_type IN ('query_unlock', 'pattern_submit', 'credit_topup', 'payout', 'network_fee')),
    amount_cents INTEGER NOT NULL,
    pattern_id UUID REFERENCES patterns(id),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tx_agent ON transactions(agent_id);
CREATE INDEX idx_tx_type ON transactions(tx_type);

-- Stripe customer mapping
CREATE TABLE IF NOT EXISTS stripe_customers (
    agent_id VARCHAR(100) PRIMARY KEY,
    stripe_customer_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Minimum sample size for pattern activation
-- Patterns with sample_size < 3 auto-deactivated
UPDATE patterns SET is_active = FALSE WHERE sample_size < 3;
