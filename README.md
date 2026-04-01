# DenialNet™ — Federated Claim Intelligence Protocol

**"The intelligence layer every claim system plugs into."**

---

## What It Is

DenialNet™ is a federated denial pattern network. Every successful denial resolution is contributed back to the network and monetized. Agents query patterns, pay contributors, and the network grows smarter with every interaction.

---

## Quick Start

```bash
# Clone
git clone https://github.com/prettybusysolutions-eng/denialnet
cd denialnet

# Install
pip install -r requirements.txt

# Seed 20 dental denial patterns
python seed_data.py

# Run
uvicorn routes:app --reload --port 8000

# Test
curl http://localhost:8000/health
curl "http://localhost:8000/patterns/query?carrier=Delta%20Dental&cpt_code=D2740&agent_id=test-agent"
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/patterns` | Submit a new denial pattern |
| POST | `/patterns/search` | Query patterns (costs credits) |
| GET | `/patterns/{id}` | Get specific pattern |
| POST | `/patterns/{id}/outcome` | Log outcome (approved/denied/partial) |
| GET | `/credits/{agent_id}` | Check balance |
| GET | `/agents/{agent_id}/transactions` | Transaction history |

---

## Query Cost & Splits

- **Query unlock:** $0.75 (configurable)
- **Submission bonus:** $0.25 per pattern
- **Contributor split:** 70% of query revenue
- **Network ops split:** 30%

---

## Pattern Schema

```json
{
  "carrier": "Delta Dental",
  "cpt_code": "D2740",
  "icd10_code": "K02.9",
  "specialty": "Dental",
  "geography": "TX",
  "denial_reason": "Missing pre-op X-ray",
  "resolution_steps": ["Attach bitewing X-ray", "Include clinical notes"],
  "attachments_required": ["xray", "clinical_notes"],
  "resubmission_format": "ADA form + attachment",
  "contributor_id": "agent-wallet-hash"
}
```

---

## Deploy to Render

1. Create PostgreSQL on Render
2. Connect GitHub repo
3. Set `DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
4. Deploy

---

## Data Moat Rules

1. You DO NOT give full patterns for free
2. You DO NOT allow scraping
3. Every interaction: contributes data OR pays for data

---

## License

Proprietary — prettybusysolutions-eng
