# Quickstart

This path runs DenialNet locally with its SQLite fallback. Stripe and Redis are
not required to evaluate the public read path.

```bash
git clone https://github.com/prettybusysolutions-eng/denialnet.git
cd denialnet
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python seed_data.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/uvicorn routes:app --host 127.0.0.1 --port 8001
```

In another terminal:

```bash
curl --fail http://127.0.0.1:8001/health
curl --fail http://127.0.0.1:8001/stats
```

The local path demonstrates the API and seeded pattern graph. It does not prove
live payer integrations, successful claim recovery, paid demand, or production
readiness.
