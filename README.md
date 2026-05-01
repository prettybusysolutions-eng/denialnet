# DenialNet

Intelligence infrastructure for revenue-critical claim workflows.

DenialNet turns repeated denial behavior into structured operational knowledge so teams can resolve faster, recover more, and stop relearning the same patterns.

## Standard
Patterns, not anecdotes.
Recovery, not noise.

## What It Is

DenialNet™ is a production-grade **federated intelligence network** for insurance claim denials. It operates as a closed-loop system where contributors submit verified denial resolution patterns, buyers query those patterns to resolve claims, and the network compounds in value with every transaction.

**The pattern graph is the product.** A structured, attributed, outcome-verified map of what actually works to reverse specific denials from specific carriers under specific circumstances.

**Not a billing company. Not a clearinghouse. An intelligence layer.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      BUYERS                              │
│   (AI agents, practice management systems, billers)     │
└────────────────────────┬────────────────────────────────┘
                         │ query (75¢) + outcome feedback
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  DENIALNET API                           │
│   FastAPI + PostgreSQL + Stripe + Redis                 │
│                                                          │
│   ┌──────────┐  ┌───────────┐  ┌────────────┐          │
│   │ Search   │  │ Preview   │  │ Contribute │          │
│   │ Engine   │  │ (free)    │  │ + Attrib.  │          │
│   └──────────┘  └───────────┘  └────────────┘          │
│                                                          │
│   ┌──────────────────────────────────────┐               │
│   │     PATTERN GRAPH                    │               │
│   │  (outcome-verified resolutions)      │               │
│   └──────────────────────────────────────┘               │
└────────────────────────┬────────────────────────────────┘
                         │ contributor royalties (70%)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   CONTRIBUTORS                            │
│   (social workers, nurses, billers, practice admins)     │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or SQLite for local dev)
- Redis 7+ (required for production; optional for dev)
- Stripe account (test mode by default)

### Local Development

```bash
# 1. Clone
git clone https://github.com/prettybusysolutions-eng/denialnet
cd denialnet

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env — set DATABASE_URL, STRIPE_SECRET_KEY, REDIS_URL

# 4. Seed data
python seed_data.py

# 5. Run
uvicorn routes:app --reload --port 8001
```

### Production Deployment (Render)

```bash
# 1. Create PostgreSQL
render.com → New → PostgreSQL → name: denialnet-db → Create

# 2. Create Redis
render.com → New → Redis → name: denialnet-redis → Create

# 3. Connect GitHub repo
render.com → New → Web Service → connect prettybusysolutions-eng/denialnet

# 4. Set environment variables
DATABASE_URL=postgresql://...    # from step 1
REDIS_URL=rediss://...           # from step 2
STRIPE_SECRET_KEY=sk_live_...    # Stripe live key
STRIPE_WEBHOOK_SECRET=whsec_...  # from Stripe Dashboard
DENIALNET_QUERY_COST_CENTS=75
SECRET_KEY=<generate-32-byte-key>

# 5. Deploy
# Note the deployed URL, e.g. https://denialnet.onrender.com

# 6. Register Stripe webhook
# Stripe Dashboard → Developers → Webhooks →
# Add endpoint: https://denialnet.onrender.com/webhooks/stripe
# Events: payment_intent.succeeded
```

---

## Core API Reference

### Free Endpoints (No Auth Required)

#### `GET /health`
Kubernetes-ready health check. Returns 200 if all systems operational.

```json
{"status": "ok", "timestamp": "2026-04-01T14:00:00Z"}
```

#### `GET /stats`
Public network statistics. No query cost.

```json
{
  "active_patterns": 71,
  "total_submissions": 71,
  "total_queries": 12,
  "total_outcomes_logged": 4,
  "average_success_rate": 0.732,
  "query_cost_cents": 75
}
```

#### `GET /patterns/preview`
**Free.** Returns top 3 matching patterns with denial reason and match level — no resolution steps. Drives conversion to paid search.

```
GET /patterns/preview?carrier=Delta%20Dental&cpt_code=D2740
```

```json
{
  "patterns": [
    {
      "pattern_id": "uuid",
      "carrier": "Delta Dental",
      "cpt_code": "D2740",
      "specialty": "Dental",
      "success_rate": 0.89,
      "sample_size": 67,
      "match_level": "exact",
      "resolution_preview": "Attach bitewing X-ray... [LOCKED]"
    }
  ],
  "total": 2,
  "preview": true,
  "cost_cents": 75,
  "message": "Unlock full resolutions for 75¢"
}
```

#### `GET /credits/{agent_id}`
Check balance. No auth required (agent_id is the identifier).

```json
{
  "agent_id": "aurex",
  "balance_cents": 14250,
  "balance_usd": 142.50,
  "query_cost_cents": 75,
  "queries_remaining": 190
}
```

#### `GET /credits/{agent_id}/transactions`
Paginated transaction history.

```
GET /credits/aurex/transactions?page=1&per_page=20
```

```json
{
  "transactions": [
    {
      "tx_id": "uuid",
      "tx_type": "query_unlock",
      "amount_cents": -75,
      "pattern_id": "uuid",
      "description": "Search unlock: Delta Dental/D2740",
      "created_at": "2026-04-01T14:00:00Z"
    }
  ],
  "page": 1,
  "per_page": 20,
  "total_count": 12
}
```

---

### Paid Endpoints (Credits Required)

#### `POST /patterns/search`
**Costs 75¢.** Returns FULL resolution steps for top matching patterns. Automatically pays contributors.

```json
POST /patterns/search
{
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "agent_id": "my-agent"
}
```

```json
{
  "patterns": [
    {
      "pattern_id": "uuid",
      "carrier": "Delta Dental",
      "cpt_code": "D2740",
      "icd10_code": "K02.9",
      "specialty": "Dental",
      "geography": "TX",
      "denial_reason": "Missing pre-op X-ray",
      "success_rate": 0.89,
      "sample_size": 67,
      "contributor_id": "system-seed",
      "resolution_steps": [
        "Attach bitewing or periapical X-ray showing decay",
        "Include clinical notes documenting caries depth",
        "Resubmit with ADA claim form attachment flag"
      ],
      "attachments_required": ["xray_periapical", "clinical_notes"],
      "resubmission_format": "ADA Claim Form + attachment"
    }
  ],
  "total": 2,
  "cost_cents": 75,
  "balance_remaining_cents": 14175,
  "contributor_paid_cents": 52,
  "network_fee_cents": 23,
  "deactivated_count": 0
}
```

#### `POST /patterns`
**Submit a new pattern.** Earns $0.25 per successful pattern when other agents query it. Rate limited: 10 submissions per 60 minutes.

```json
POST /patterns
{
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "icd10_code": "K02.9",
  "specialty": "Dental",
  "geography": "TX",
  "denial_reason": "Missing pre-op X-ray",
  "resolution_steps": [
    "Attach bitewing X-ray",
    "Include clinical notes"
  ],
  "attachments_required": ["xray", "clinical_notes"],
  "resubmission_format": "ADA form + attachment",
  "contributor_id": "my-agent"
}
```

Response:
```json
{
  "pattern_id": "uuid",
  "approved": true,
  "message": "Pattern live. You'll earn 70% of each query."
}
```

#### `POST /patterns/{id}/outcome`
**Log an outcome** to improve pattern accuracy. Required for contributor reputation scoring.

```json
POST /patterns/uuid/outcome
{
  "outcome": "approved",
  "agent_id": "my-agent"
}
```

Valid outcomes: `approved`, `denied`, `partial`

#### `GET /patterns/{id}`
Get a specific pattern by UUID. Requires active balance or pattern ownership.

---

### Bulk Operations

#### `POST /patterns/ingest`
**Bulk import patterns from CSV.** For organizations contributing multiple patterns at once.

```json
POST /patterns/ingest
{
  "contributor_id": "my-org",
  "patterns_csv": "carrier,cpt_code,icd10_code,specialty,geography,denial_reason,resolution_steps,attachments_required,resubmission_format\nDelta Dental,D2740,K02.9,Dental,TX,Missing X-ray,\"[\\\"Attach X-ray\\\",\\\"Resubmit\\\"]\",\"[\\\"xray\\\"]\",\"ADA form\""
}
```

Response:
```json
{
  "accepted_count": 2,
  "rejected_count": 0,
  "total_bonus_cents": 50,
  "accepted": [{"row": 2, "carrier": "Delta Dental", "cpt_code": "D2740", "bonus_cents": 25}],
  "rejected": []
}
```

---

### Stripe Topup

#### `POST /credits/topup`
Create a Stripe PaymentIntent for adding credits.

```json
POST /credits/topup
{
  "agent_id": "my-agent",
  "amount_cents": 5000,
  "stripe_token": "tok_visa"
}
```

Response:
```json
{
  "client_secret": "pi_xxx_secret_xxx",
  "amount_cents": 5000,
  "status": "requires_payment_method"
}
```

#### `POST /credits/topup/confirm`
Confirm the payment and add credits to agent balance.

```json
POST /credits/topup/confirm
{
  "payment_intent_id": "pi_xxx"
}
```

---

## Data Model

### Pattern
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `carrier` | String(100) | Insurance carrier name |
| `cpt_code` | String(20) | CPT procedure code |
| `icd10_code` | String(20) | ICD-10 diagnosis code (nullable) |
| `specialty` | String(50) | Medical specialty |
| `geography` | String(10) | State/region code (nullable) |
| `denial_reason` | Text | Structured denial reason |
| `resolution_steps` | JSON | Array of resolution actions |
| `attachments_required` | JSON | Required documentation |
| `resubmission_format` | String(255) | How to resubmit |
| `success_rate` | Float | Historical approval rate |
| `sample_size` | Integer | Number of verified outcomes |
| `is_active` | Boolean | Pattern is live |
| `contributor_id` | String(100) | Contributor wallet/ID |
| `created_at` | DateTime | Pattern creation time |
| `updated_at` | DateTime | Last outcome update |

### PatternOutcome
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `pattern_id` | UUID | FK to Pattern |
| `outcome` | Enum | approved / denied / partial |
| `agent_id` | String(100) | Who logged it |
| `logged_at` | DateTime | When logged |

### AgentBalance
| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | String(100) | Primary key |
| `balance_cents` | Integer | Current balance |
| `updated_at` | DateTime | Last change |

### Transaction
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | String(100) | Affected agent |
| `tx_type` | String(50) | Type of transaction |
| `amount_cents` | Integer | Positive = credit, negative = debit |
| `pattern_id` | UUID | Related pattern (nullable) |
| `description` | String(255) | Human-readable description |
| `created_at` | DateTime | Transaction time |

### RateLimit
| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `agent_id` | String(100) | Agent identifier |
| `endpoint` | String(50) | Which endpoint limited |
| `window_start` | DateTime | Rate limit window |
| `request_count` | Integer | Requests in window |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /patterns/search` | 20 requests | 60 minutes |
| `POST /patterns` | 10 requests | 60 minutes |
| `POST /patterns/ingest` | 5 requests | 60 minutes |

When rate limited, returns HTTP 429:
```json
{
  "error": "rate_limit_exceeded",
  "endpoint": "search",
  "limit": 20,
  "window_minutes": 60,
  "reset_at": "2026-04-01T14:00:00Z"
}
```

---

## Revenue Split

Every paid query distributes:
- **70%** → Pattern contributor
- **23%** → Network operations (infrastructure, support, development)
- **7%** → DenialNet improvement fund (R&D, new features)

---

## Production Requirements

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes (prod) | Redis connection string |
| `STRIPE_SECRET_KEY` | Yes (prod) | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Yes (prod) | `whsec_...` |
| `SECRET_KEY` | Yes (prod) | 32-byte secret for session signing |
| `DENIALNET_QUERY_COST_CENTS` | No | Default: 75 |
| `QUERY_COST_CENTS` | No | Alias for above |
| `CONTRIBUTOR_SPLIT` | No | Default: 0.70 |
| `RATE_LIMIT_SEARCH` | No | Default: 20 |
| `RATE_LIMIT_SUBMIT` | No | Default: 10 |
| `RATE_LIMIT_WINDOW_MINUTES` | No | Default: 60 |
| `MIN_SAMPLE_SIZE` | No | Default: 3 |
| `MIN_SUCCESS_RATE` | No | Default: 0.30 |
| `DATABASE_URL` | Dev | SQLite path: `sqlite:///./denialnet.db` |

---

## Production Gaps — Upgrade Roadmap

### Phase 1: Security Hardening (Must Complete Before Live Payments)
- [x] **API Key Authentication**: ✅ X-API-Key header required on paid endpoints. Keys SHA-256 hashed in `api_keys` table. Admin endpoints: POST/GET/DELETE /admin/keys. Auth: X-Admin-Key header.
- [x] **Stripe Webhook Signature Verification**: ✅ `stripe.Webhook.construct_event()` enforced. No raw JSON fallback. Rejects all unsigned requests.
- [x] **Webhook Dead Letter Queue**: ✅ Failed events stored in `webhook_dlq` table. Retry: POST /admin/dlq/retry (X-Admin-Key, max 5 retries). Status: GET /admin/dlq.
- [ ] **Input Validation Hardening**: Pydantic models enforce strict type + range constraints. Regex validation for agent_id, cpt_code.
- [ ] **SQL Injection Prevention**: All queries use SQLAlchemy parameterized statements. No raw string interpolation.

### Phase 2: Reliability (Must Complete Before Production Traffic)
- [x] **Redis-Backed Rate Limiting**: ✅ Redis client initialized lazily with in-memory DB fallback. Graceful Redis failure handling.
- [ ] **Database Migrations**: Use Alembic for schema versioning. No manual schema changes.
- [ ] **Connection Pooling**: PostgreSQL connection pool (PgBouncer or built-in). Replace NullPool with QueuePool.
- [ ] **Graceful Shutdown**: uvicorn handles SIGTERM, drains connections, finishes in-flight requests.
- [ ] **Health/Ready/Live Probes**: `/health` returns 200. `/ready` checks DB + Redis connectivity.

### Phase 3: Observability (Must Complete Before Incident Response)
- [ ] **Structured Logging**: JSON logs with request_id, agent_id, pattern_id, duration_ms. Every request traceable.
- [ ] **Metrics**: Prometheus metrics — query latency, error rate, credit flow, pattern growth rate.
- [ ] **Alerting**: PagerDuty/OpsGenie integration. Alert on: error rate >1%, webhook failure rate >5%, balance near zero.
- [ ] **APM**: OpenTelemetry traces for all API requests. Full span from API call to DB query to Stripe API.
- [ ] **Audit Log**: Immutable log of all balance-affecting transactions with timestamp, agent_id, amount, pattern_id.

### Phase 4: Scalability (Before Multi-Region or High Traffic)
- [ ] **Redis Cluster**: Redis Sentinel or Cluster for HA. Current single-node Redis is SPOF.
- [ ] **Read Replicas**: PostgreSQL read replica for `/stats` and `/preview` endpoints.
- [ ] **CDN**: Cloudflare or Fastly in front. Cache `/stats` and `/patterns/preview` at edge.
- [ ] **Auto-Scaling**: Render auto-scaling rules based on p95 latency + error rate.

### Phase 5: Business Logic
- [ ] **Contributor Reputation Score**: Weighted success rate based on sample size + outcome consistency + time since last update.
- [ ] **Pattern Expiry**: Patterns with no new outcomes in 12 months flagged for review.
- [ ] **Dispute Resolution**: When an outcome is logged as `denied`, contributor can challenge within 48h.
- [ ] **Bulk Contract Pricing**: Enterprise buyers negotiate flat-rate API access instead of per-query.
- [ ] **Geographic Expansion**: Multi-state pattern graph. Carrier-specific models for TX, FL, CA, NY.

---

## Project Structure

```
denialnet/
├── routes.py              # FastAPI app + all endpoints
├── models.py              # SQLAlchemy models
├── database.py            # DB connection + session management
├── config.py              # Environment variable parsing
├── schema.sql             # Raw PostgreSQL schema (backup reference)
├── app.py                 # Application factory + lifecycle hooks
├── seed_data.py           # 50 seed patterns + initial balances
├── requirements.txt       # Python dependencies
├── render.yaml            # Render deployment config
├── Procfile               # Render process type
├── .env.example           # Environment variable template
├── scripts/
│   ├── agent_cli.py       # CLI tool for agents
│   ├── smoke_test         # Local smoke test suite
│   └── install            # Production install script
├── SPEC.md                # Full specification document
└── README.md              # This file
```

---

## Glossary

| Term | Definition |
|------|------------|
| **Pattern** | A verified denial resolution with success rate and sample size |
| **Contributor** | Agent who submits resolution patterns and earns royalties |
| **Buyer** | Agent who pays to unlock resolution patterns |
| **Attribution Ledger** | Immutable record of every payment split |
| **Pattern Graph** | The full network of all patterns and their relationships |
| **Success Rate** | % of submissions using this pattern that resulted in approval |
| **Sample Size** | Number of verified outcomes contributing to success rate |
| **Min-Sample Enforcement** | Patterns auto-deactivate if sample < 3 AND success_rate < 30% |

---

## License

Proprietary. © 2026 PrettyBusySolutions Engineering. All rights reserved.

---

**Built with precision. Deployed with confidence. Operated with intelligence.**
