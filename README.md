# DenialNet™ — Federated Claim Intelligence Protocol

**"The intelligence layer every claim system plugs into."**

---

## What It Is

DenialNet™ is a federated denial pattern network. Every successful denial resolution is contributed back to the network and monetized. Agents query patterns, pay contributors, and the network grows smarter with every interaction.

**Not a billing company. Not a clearinghouse. An intelligence layer.**

---

## Quick Start

```bash
git clone https://github.com/prettybusysolutions-eng/denialnet
cd denialnet
pip install -r requirements.txt
python seed_data.py
uvicorn routes:app --reload --port 8000
```

Test:
```bash
curl http://localhost:8000/health
curl "http://localhost:8000/patterns/preview?carrier=Delta%20Dental&cpt_code=D2740"
curl -X POST http://localhost:8000/patterns/search \
  -H "Content-Type: application/json" \
  -d '{"carrier":"Delta Dental","cpt_code":"D2740","agent_id":"my-agent"}'
```

---

## Deploy to Render

1. **Create PostgreSQL:** render.com → New → PostgreSQL → `denialnet-db`
2. **Connect repo:** render.com → New → Web Service → connect `prettybusysolutions-eng/denialnet`
3. **Set env vars:**
   - `DATABASE_URL` = PostgreSQL connection string
   - `STRIPE_SECRET_KEY` = `sk_live_...` (optional)
   - `DENIALNET_QUERY_COST_CENTS=75`
4. **Deploy** → note your URL
5. **Stripe webhook:** register `https://<your-url>/webhook/stripe` for `payment_intent.succeeded`

---

## API Reference

### Public Endpoints

#### `GET /health`
Health check.
```json
{"status": "ok", "service": "DenialNet™", "version": "0.1.0"}
```

#### `GET /stats`
Public network statistics.
```json
{
  "active_patterns": 20,
  "total_submissions": 20,
  "total_queries": 5,
  "total_outcomes_logged": 2,
  "average_success_rate": 0.746,
  "query_cost_cents": 75
}
```

#### `GET /patterns/preview`
Free preview — shows top 3 patterns WITHOUT resolution steps. Converts free users to paid.
```
GET /patterns/preview?carrier=Delta%20Dental&cpt_code=D2740&icd10_code=K02.9&specialty=Dental
```
```json
{
  "patterns": [
    {
      "pattern_id": "741fdce2-...",
      "carrier": "Delta Dental",
      "cpt_code": "D2740",
      "specialty": "Dental",
      "success_rate": 0.892,
      "sample_size": 68,
      "match_level": "exact",
      "resolution_preview": "Attach bitewing or periapical X-ray showing decay • Include clinical notes..."
    }
  ],
  "total": 1,
  "preview": true,
  "cost_cents": 75,
  "message": "Unlock full resolutions for 75¢ — or submit your own pattern for free."
}
```

#### `GET /credits/{agent_id}`
Check credit balance.
```json
{
  "agent_id": "my-agent",
  "balance_cents": 5000,
  "balance_usd": 50.00,
  "query_cost_cents": 75,
  "queries_remaining": 66
}
```

---

### Authenticated Endpoints

All authenticated endpoints require no API key for v0.1 (agent_id passed in body). Rate limiting and API keys coming in v0.2.

#### `POST /patterns`
Submit a new denial pattern. Earn $0.25 when another agent queries it.
```json
{
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "icd10_code": "K02.9",
  "specialty": "Dental",
  "geography": "TX",
  "denial_reason": "Missing pre-op X-ray",
  "resolution_steps": [
    "Attach bitewing or periapical X-ray showing decay",
    "Include clinical notes documenting caries depth",
    "Resubmit with ADA claim form attachment flag"
  ],
  "attachments_required": ["xray_periapical", "clinical_notes"],
  "resubmission_format": "ADA Claim Form + attachment",
  "contributor_id": "my-agent"
}
```
Response:
```json
{
  "ok": true,
  "pattern_id": "3dc042dc-...",
  "submission_bonus_cents": 25,
  "message": "Pattern submitted. You'll earn 75¢ every time an agent unlocks it."
}
```

#### `POST /patterns/search`
Query patterns. Costs 75¢. Returns full resolution steps.
```json
{
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "icd10_code": "K02.9",
  "agent_id": "my-agent"
}
```
Response:
```json
{
  "patterns": [
    {
      "pattern_id": "741fdce2-...",
      "carrier": "Delta Dental",
      "cpt_code": "D2740",
      "denial_reason": "Missing pre-op X-ray",
      "resolution_steps": [
        "Attach bitewing or periapical X-ray showing decay",
        "Include clinical notes documenting caries depth",
        "Resubmit with ADA claim form attachment flag"
      ],
      "attachments_required": ["xray_periapical", "clinical_notes"],
      "resubmission_format": "ADA Claim Form + attachment",
      "success_rate": 0.892,
      "sample_size": 68
    }
  ],
  "total": 1,
  "cost_cents": 75,
  "balance_remaining_cents": 4925,
  "contributor_paid_cents": 52,
  "network_fee_cents": 23
}
```

#### `GET /patterns/{pattern_id}`
Get specific pattern. Requires prior unlock or submission.
```json
{
  "pattern_id": "741fdce2-...",
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "resolution_steps": ["..."],
  ...
}
```

#### `POST /patterns/{pattern_id}/outcome`
Log outcome of using a pattern. Updates success_rate.
```json
{
  "outcome": "approved",
  "submitted_by": "my-agent",
  "notes": "Third attempt, finally approved after adding X-ray"
}
```
Response:
```json
{
  "ok": true,
  "pattern_id": "741fdce2-...",
  "outcome_recorded": "approved",
  "new_success_rate": 0.895,
  "new_sample_size": 69,
  "is_active": true,
  "deactivated": false
}
```

#### `GET /credits/{agent_id}/transactions`
Paginated transaction history.
```
GET /credits/my-agent/transactions?limit=20&offset=0
```
```json
{
  "agent_id": "my-agent",
  "transactions": [
    {
      "id": "tx-uuid",
      "type": "query_unlock",
      "amount_cents": -75,
      "amount_usd": -0.75,
      "pattern_id": "741fdce2-...",
      "description": "Search unlock: Delta Dental/D2740",
      "created_at": "2026-04-01T12:00:00"
    }
  ],
  "total": 10,
  "limit": 20,
  "offset": 0
}
```

#### `POST /credits/topup`
Create Stripe PaymentIntent for credit topup.
```json
{
  "agent_id": "my-agent",
  "stripe_customer_id": "cus_...",
  "stripe_payment_method_id": "pm_...",
  "amount_cents": 5000
}
```
Response (test mode — no Stripe key):
```json
{
  "ok": true,
  "mode": "test",
  "agent_id": "my-agent",
  "amount_cents": 5000,
  "amount_usd": 50.00,
  "new_balance_cents": 5500
}
```

---

## Revenue Model

| Action | Amount | Split |
|--------|--------|-------|
| Query unlock | $0.75 | 70% contributor, 30% network |
| Pattern submission bonus | $0.25 | 100% to contributor |
| Stripe topup | $5-$1000 | 100% credit added |

---

## Success Rate Formula

Exponential Moving Average (EMA):
```
new_rate = (old_rate × n + new_outcome) / (n + 1)
where new_outcome = 1.0 (approved), 0.5 (partial), 0.0 (denied)
```

Auto-deactivation condition:
```
sample_size < 3 AND success_rate < 0.30 → is_active = False
```

---

## Context Nexus Marketplace Integration

DenialNet is registered as a service on the Context Nexus marketplace:
- **Slug:** denialnet-pro
- **Price:** $0.75/query
- **Triggers:** denial_detected, claim_rejected, insurance_denial
- **Split:** 3% ops, 70% provider, 27% improvement fund

Buyer agents can declare policies:
```bash
nexus_market action=declare_policy \
  policy_name="Auto dental denial buyer" \
  category=security \
  max_budget_amount=200.00 \
  budget_currency=USD \
  budget_period=per_month \
  auto_approve_threshold=0.5 \
  trigger_signals='["denial_detected","insurance_denial"]'
```

---

## Data Moat Rules

1. **You DO NOT give full patterns for free** — preview only
2. **You DO NOT allow scraping** — rate limiting in v0.2
3. **Every interaction: contributes data OR pays for data**

---

## License

Proprietary — prettybusysolutions-eng
