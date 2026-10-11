# DenialNet

Prototype API for contributing, searching, and unlocking insurance denial patterns.
Seed data is synthetic; reported seed success rates are not independently verified outcomes.

## Local setup

Requires Python 3.11+.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DENIALNET_ADMIN_API_KEY to a generated secret.
uvicorn app:app --port 8001
```

All application configuration uses the `DENIALNET_` prefix. SQLite is the local default.
`app:app` and `routes:app` expose the same application. `/docs` describes request schemas.
`/health` is liveness; `/ready` checks configured dependencies.

## Authentication and payment flow

An administrator creates an account-bound key through `POST /admin/keys` with
`X-Admin-Key`; include a nonempty `agent_id`. Clients send `X-API-Key`.
The key's account must match any submitted account identity. Balance and transaction
reads require that same account. Pattern reads require ownership or a paid unlock;
free previews do not include resolution steps. Each paid search grants durable access
to every returned pattern. Contributor credits are internal ledger balances, not bank payouts.

Create a topup through `POST /credits/topup`. Complete the returned Stripe PaymentIntent
client-side, then confirm it or let the signed `payment_intent.succeeded` webhook settle it.
The server verifies the stored account binding, amount, currency and succeeded status.
A unique receipt, balance increment and ledger transaction commit atomically, so repeated
confirmations, webhooks and DLQ retries share one settlement record.
Missing Stripe configuration returns an error; it never silently issues free credits.
Mock crediting requires both `DENIALNET_ENV=test` and `DENIALNET_ALLOW_MOCK_PAYMENTS=true`.

## Release and migration requirements

Production startup requires `DENIALNET_ENV=production`, a PostgreSQL
`DENIALNET_DATABASE_URL`, live `DENIALNET_STRIPE_SECRET_KEY`,
`DENIALNET_STRIPE_WEBHOOK_SECRET`, and `DENIALNET_ADMIN_API_KEY`.
Set Redis configuration as appropriate and verify `/ready` before routing traffic.
Configure Stripe to deliver `payment_intent.succeeded` to `/webhooks/stripe`.

Back up the database before upgrading. Startup creates the new `pattern_entitlements`,
`topup_intents` and `payment_receipts` tables through SQLAlchemy metadata; there is no
versioned migration framework yet. Rehearse against a database copy first. Existing
unbound API keys must be replaced with account-bound keys. Historical payments have
no server-created binding and are deliberately refused by automatic settlement: reconcile
them against Stripe and the existing ledger manually before crediting anything. Historical
pattern unlocks also require an audited entitlement migration; this patch does not guess
which accounts purchased which patterns. Do not delete receipts on rollback.

No production deployment, live Stripe payment, or PostgreSQL concurrency test was performed
for this change. Those staging checks remain release gates. This is not a production-readiness
or clinical-validity certification.

## Verification

```sh
pip install pytest httpx
python -m pytest -q
pip check
```

Tests isolate a temporary SQLite database and exercise account isolation, paid access,
invalid payments, rollback/retry, signed-webhook rejection and concurrent duplicate settlement.
The deployed read-only smoke script requires `DENIALNET_URL`, `DENIALNET_AGENT_ID`,
and `DENIALNET_API_KEY`: `python scripts/smoke_test`.
The example CLI also reads `DENIALNET_API_KEY`.

## Reconciliation provenance

Baseline: `a3a3fd574c0c7732600a6a754b14d911385bb299`.
Backup: `xzenia-private-backup@01a883c1e3a7155df64e50af8eddedcdb97669d5`.
Recovered the application entrypoint; retained newer standalone behavior and repaired
account access, settlement and environment handling directly. The backup's older marketing
README was not promoted.

## License

Proprietary. © 2026 PrettyBusySolutions Engineering. All rights reserved.
