# Release diff and staging review — 2026-09-19

Status: release gate OPEN. This is an author-side engineering review, not independent third-party certification or proof of a production release.

Reviewed published PR #12 final candidate head `6907b1911644f8487196cc768cb5471b343a0763`.

## Findings corrected

- Creating a missing contributor balance committed a pending buyer debit and entitlements before contributor settlement finished. The helper now flushes within the caller's transaction. Failure injection after balance creation verifies rollback of the debit, entitlements and ledger.
- Quality enforcement ran after selecting paid results, allowing deactivated patterns to be sold. It now runs before selection. A regression verifies no charge when only low-quality patterns match.

## Evidence

Local `.venv/bin/python -m pytest -q`: **21 passed, 1 skipped**, with three dependency deprecation warnings. GitHub's PostgreSQL 16 plus Redis service-container workflow passed, including isolated schemas and shared-worker rate-limit checks. Stripe inputs remain synthetic; no live Stripe settlement was performed.

## Staging gate remains open

No dedicated staging URL, PostgreSQL service or Stripe test credentials were available in this workspace. No customer payments, production data changes or deployment were attempted. Local PostgreSQL installation failed because the environment denied package-manager identity changes; no PostgreSQL migration rehearsal was completed.

Before release: deploy the exact candidate to isolated staging; rehearse existing-schema migration and rollback against a representative sanitized PostgreSQL copy; run concurrent purchase/top-up settlement there; create and confirm a real Stripe test-mode payment; replay signed delivery and verify exactly one durable credit after restart; verify readiness, authentication and ledger reconciliation over HTTP. Capture candidate SHA and provider event IDs without secrets.

`DENIALNET_ENV=staging` now requires PostgreSQL, `sk_test_` credentials, webhook/admin secrets and disabled mock payments. Production still requires live credentials. Contributor rewards now increment balances atomically. Readiness checks all model tables/columns and rejects missing schema without exposing database error details. Multi-worker rate-limit behavior and deployed recovery still need staging coverage.

Infrastructure discovery: no Render/Stripe/database configuration variables were present. The repository's candidate `https://denialnet.onrender.com/ready` returned HTTP 404. A new Neon connection was confirmed by the application; no Neon database has been provisioned or tested by this review.

Passing local tests or CI alone does not close this gate.
