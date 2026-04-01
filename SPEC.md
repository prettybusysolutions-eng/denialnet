# DenialNet™ — Federated Claim Intelligence Protocol
## v0.1 — Minimal Dominance Build

---

## What It Is

The economic substrate for denied-claim intelligence.
Not a tool. Not a billing company. An intelligence layer every claim system plugs into.

**Positioning:** "The intelligence layer every claim system plugs into."

---

## Core Product

**Pattern Unit** (atomic object):
```json
{
  "pattern_id": "hash",
  "carrier": "Cigna",
  "cpt_code": "D2740",
  "icd10_code": "K02.9",
  "specialty": "Dental",
  "geography": "TX",
  "denial_reason": "Missing narrative",
  "resolution_steps": ["Attach clinical narrative", "Include pre-op X-ray", "Use specific wording: 'functional impairment'"],
  "attachments_required": ["xray", "clinical_notes"],
  "resubmission_format": "EDI + attachment",
  "success_rate": 0.87,
  "sample_size": 34,
  "created_at": "timestamp",
  "contributor_id": "wallet_hash"
}
```

**No fluff fields. Only fields that increase approval probability.**

---

## Architecture

### Stack
- FastAPI (Python)
- PostgreSQL (Render — same stack as LeakLock)
- SQLAlchemy ORM
- Stripe for payments (v0.1 simple)

### Revenue Model
- Query unlock: $0.25–$2.00
- Split: 70% contributor, 30% network ops
- Internal credit balance (avoid per-transaction friction)

### Query Logic
Rule-based matching, not AI:
- carrier match (hard filter)
- CPT code match (high weight)
- ICD-10 match (medium weight)
- denial_reason similarity (low weight, embedding optional later)
- Rank by: success_rate DESC, sample_size DESC

---

## Endpoints (v0.1)

### `POST /patterns` — Submit a pattern
### `POST /patterns/search` — Query patterns (costs credits)
### `GET /patterns/{id}` — Get specific pattern
### `POST /patterns/{id}/outcome` — Log outcome (update success_rate)
### `GET /credits/{agent_id}` — Check credit balance
### `GET /agents/{agent_id}/transactions` — Transaction history
### `GET /health` — Health check

---

## Data Moat Rules

1. You DO NOT give full patterns for free
2. You DO NOT allow scraping
3. Every interaction: contributes data OR pays for data

---

## Seed Strategy

50-100 patterns manually seeded:
- Dental (fastest vertical)
- High-frequency CPT codes
- Common denials

---

## Target Metrics

- 500 clinics × 20 queries/day × $0.75 avg = $225K/month (early stage)
- Compounding as network grows

---

## Compliance

- Only store: codes, patterns, resolutions
- NO patient identifiers
- HIPAA-aligned: de-identified data only
