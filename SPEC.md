# DenialNet™ — Federated Claim Intelligence Protocol

## v0.1 — Complete Robust Build

---

## What It Is

**"The intelligence layer every claim system plugs into."**

DenialNet™ is a federated denial pattern network. Every successful denial resolution is contributed back to the network and monetized. Agents query patterns, pay contributors, and the network grows smarter with every interaction.

Not a billing company. Not a clearinghouse. An intelligence layer.

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
- FastAPI (Python 3.8+, uvicorn)
- PostgreSQL (SQLite for local dev)
- SQLAlchemy ORM
- Stripe (payments + topup)
- Deployed on Render (single service + DB)

### Matching Logic
Rule-based scoring (v0.1):
```
score = carrier_match(30%) + CPT_match(35%) + ICD10_match(20%) + denial_reason_similarity(15%)
```
Ranked by: `success_rate DESC, sample_size DESC`

---

## API Endpoints (v0.1 — Complete)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/` | None | Root info |
| GET | `/stats` | None | Public network statistics |
| GET | `/patterns/preview` | None | Free preview — top 3 without resolution steps |
| POST | `/patterns` | API | Submit new denial pattern |
| POST | `/patterns/search` | API | Query patterns (costs credits) |
| GET | `/patterns/{id}` | API | Get specific pattern by ID |
| POST | `/patterns/{id}/outcome` | API | Log outcome (approved/denied/partial) |
| GET | `/credits/{agent_id}` | None | Check credit balance |
| GET | `/credits/{agent_id}/transactions` | None | Paginated transaction history |
| POST | `/credits/topup` | API | Create Stripe PaymentIntent for topup |
| POST | `/credits/topup/confirm` | API | Confirm topup, add credits |

---

## Revenue Model

### Query Unlock
- **Cost:** $0.75 per search (configurable via `DENIALNET_QUERY_COST_CENTS`)
- **Split:** 70% contributor, 30% network ops

### Pattern Submission
- **Bonus:** $0.25 per submitted pattern
- **Earns when:** another agent queries and unlocks the pattern

### Stripe Topup
- **Minimum:** $5.00 (500¢)
- **Maximum:** $1,000.00 per transaction
- **Mode:** Test mode if no Stripe key set; live Stripe if key provided

---

## Data Moat Rules

1. You DO NOT give full patterns for free
2. You DO NOT allow scraping
3. Every interaction: contributes data OR pays for data
4. Patterns with `sample_size < 3` AND `success_rate < 0.30` are **auto-deactivated**

---

## Success Validation Loop

Every time a pattern is reused:
```
agent queries → 
applies resolution → 
outcome logged (approved/denied/partial) →
success_rate updated (EMA) →
if sample_size < 3 AND rate < 0.30 → auto-deactivated
```

---

## Min-Sample Enforcement

Patterns are auto-deactivated if:
```
sample_size < MIN_SAMPLE_SIZE (default: 3)
AND
success_rate < 0.30
```

This prevents low-quality patterns from misleading buyers.

---

## Preview Conversion Funnel

```
/patterns/preview (FREE)
    ↓
Shows: carrier, CPT, specialty, success_rate, sample_size, 2-step preview
    ↓
"Unlock full resolutions for 75¢"
    ↓
/patterns/search (PAID)
    ↓
Full resolution steps + attachments + resubmission format
```

---

## Seed Data (20 Patterns)

Dental high-frequency CPT codes:
- D2740 (Crown) — 3 carriers
- D2335 (Composite Anterior) — 2 carriers
- D0150 (Comprehensive Exam) — 2 carriers
- D4341 (Periodontal Scaling) — 2 carriers
- D7210 (Extraction) — 2 carriers
- D2391, D9222, D8680, D4260, D1555, D1354, D4910, D0250, D6080 — 1 carrier each

All seeded with realistic success rates and sample sizes from "system-seed" contributor.

---

## Deployment

### Render
1. Create PostgreSQL: `render.com → New → PostgreSQL → denialnet-db`
2. Create Web Service: `render.com → New → Web Service → connect denialnet repo`
3. Set env vars:
   - `DATABASE_URL` = PostgreSQL connection string
   - `STRIPE_SECRET_KEY` = `sk_live_...` (optional for live payments)
   - `STRIPE_WEBHOOK_SECRET` = `whsec_...`
   - `DENIALNET_QUERY_COST_CENTS` = `75`
   - `DENIALNET_CONTRIBUTOR_SPLIT` = `0.70`
4. Deploy → get URL
5. Stripe Dashboard → register webhook for `payment_intent.succeeded`

### Local Dev
```bash
pip install -r requirements.txt
python seed_data.py
uvicorn routes:app --reload --port 8000
```

---

## Compliance

- Only store: codes, patterns, resolutions
- NO patient identifiers
- HIPAA-aligned: de-identified data only
- Stripe PCI-DSS compliant for payment data

---

## Target Metrics

- 500 clinics × 20 queries/day × $0.75 = **$225K/month** (early stage)
- Compounding as network grows through data gravity + income lock-in

---

## Defensibility

1. Patterns > competitors
2. Success rates proven
3. Contributors earning real money
4. Switching cost = losing revenue stream

---

## Status

**v0.1 — COMPLETE ROBUST BUILD** ✅

All spec items implemented:
- [x] Pattern schema
- [x] Ingest pipeline (submit + outcome)
- [x] Success validation loop (EMA update)
- [x] Query engine (ranked by success_rate)
- [x] Attribution + payments (split table)
- [x] Stripe integration (topup + confirm)
- [x] Preview endpoint (conversion funnel)
- [x] Min-sample enforcement
- [x] 20 seed patterns
- [x] Paginated transactions
- [x] Public stats endpoint
- [x] Render deployment config

---

## License

Proprietary — prettybusysolutions-eng
