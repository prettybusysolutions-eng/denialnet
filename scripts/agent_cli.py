#!/usr/bin/env python3
"""
DenialNet CLIAgent — Autonomous denial handling for AI agents
Usage: python3 agent_cli.py --carrier "Delta Dental" --cpt D2740 --icd10 K02.9 --denial "Missing pre-op X-ray"

This script shows how an AI agent integrates DenialNet autonomously:
1. Receives denial signal
2. Previews patterns (free)
3. Unlocks resolution if policy approves
4. Logs outcome
5. Reports to operator
"""
import argparse
import json
import sys
import os

DENIALNET_URL = os.environ.get("DENIALNET_URL", "http://localhost:8001")
AGENT_ID = os.environ.get("DENIALNET_AGENT_ID", "agent-cli")


def preview(carrier, cpt_code, icd10=None, specialty=None):
    from urllib.parse import urlencode
    params = [
        ("carrier", carrier),
        ("cpt_code", cpt_code),
    ]
    if icd10:
        params.append(("icd10_code", icd10))
    if specialty:
        params.append(("specialty", specialty))
    import urllib.request
    try:
        url = f"{DENIALNET_URL}/patterns/preview?" + urlencode(params)
        with urllib.request.urlopen(url) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def search(carrier, cpt_code, icd10=None, denial_reason=None, specialty=None, agent_id=AGENT_ID):
    import urllib.request
    body = json.dumps({
        "carrier": carrier,
        "cpt_code": cpt_code,
        "icd10_code": icd10,
        "denial_reason": denial_reason,
        "specialty": specialty,
        "agent_id": agent_id,
    }).encode()
    req = urllib.request.Request(
        f"{DENIALNET_URL}/patterns/search",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read())}


def get_outcome(pattern_id, outcome, submitted_by=AGENT_ID, notes=None):
    import urllib.request
    body = json.dumps({
        "outcome": outcome,
        "submitted_by": submitted_by,
        "notes": notes,
    }).encode()
    req = urllib.request.Request(
        f"{DENIALNET_URL}/patterns/{pattern_id}/outcome",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def get_balance(agent_id=AGENT_ID):
    import urllib.request
    try:
        with urllib.request.urlopen(f"{DENIALNET_URL}/credits/{agent_id}") as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="DenialNet CLIAgent — autonomous denial handling")
    parser.add_argument("--carrier", required=True, help="Insurance carrier name")
    parser.add_argument("--cpt", required=True, help="CPT code")
    parser.add_argument("--icd10", help="ICD-10 code")
    parser.add_argument("--specialty", default="Dental", help="Medical specialty")
    parser.add_argument("--denial", help="Denial reason")
    parser.add_argument("--agent-id", default=AGENT_ID, help="Agent ID for balance tracking")
    parser.add_argument("--auto", action="store_true", help="Auto-approve and apply resolution")
    parser.add_argument("--approve", choices=["approved", "denied", "partial"], help="Log outcome")
    parser.add_argument("--balance", action="store_true", help="Check balance only")
    args = parser.parse_args()

    if args.balance:
        bal = get_balance(args.agent_id)
        print(f"[DenialNet] Agent: {args.agent_id}")
        print(f"  Balance: ${bal['balance_usd']} ({bal['balance_cents']}¢)")
        print(f"  Queries remaining: {bal['queries_remaining']}")
        return

    print(f"[DenialNet] Processing denial:")
    print(f"  Carrier: {args.carrier}")
    print(f"  CPT: {args.cpt}")
    if args.icd10:
        print(f"  ICD-10: {args.icd10}")
    if args.denial:
        print(f"  Denial reason: {args.denial}")

    # Step 1: Preview (free)
    print(f"\n[Step 1] Previewing patterns (free)...")
    prev = preview(args.carrier, args.cpt, args.icd10, args.specialty)
    if "error" in prev:
        print(f"  Error: {prev['error']}")
        sys.exit(1)
    if not prev.get("patterns"):
        print(f"  No patterns found. Submit one!")
        sys.exit(0)

    for p in prev["patterns"]:
        print(f"  ✓ {p['carrier']} {p['cpt_code']} | rate={p['success_rate']} | samples={p['sample_size']}")
        print(f"    preview: {p['resolution_preview']}")

    # Step 2: Unlock if auto-approved
    if args.auto:
        print(f"\n[Step 2] Auto-unlocking resolution (costs {prev['cost_cents']}¢)...")
        result = search(args.carrier, args.cpt, args.icd10, args.denial, args.specialty, args.agent_id)
        if "error" in result:
            if isinstance(result["error"], dict) and result["error"].get("error") == "insufficient_credits":
                print(f"  ✗ Insufficient credits: need {result['error']['needed_cents']}¢, have {result['error']['current_cents']}¢")
                print(f"  → Top up: curl -X POST {DENIALNET_URL}/credits/topup -d '{{\"agent_id\":\"{args.agent_id}\",\"amount_cents\":5000}}'")
                sys.exit(1)
            print(f"  Error: {result['error']}")
            sys.exit(1)

        top = result["patterns"][0]
        print(f"  ✓ Resolution unlocked:")
        print(f"    denial: {top['denial_reason']}")
        for i, step in enumerate(top["resolution_steps"], 1):
            print(f"    {i}. {step}")
        if top.get("attachments_required"):
            print(f"    attachments: {', '.join(top['attachments_required'])}")
        print(f"  Cost: {result['cost_cents']}¢ | Balance remaining: {result['balance_remaining_cents']}¢")
        print(f"  Contributor paid: {result['contributor_paid_cents']}¢")
    else:
        print(f"\n  → To unlock: python3 agent_cli.py --carrier '{args.carrier}' --cpt {args.cpt} --auto")

    if args.approve:
        # Get pattern_id from search result
        result = search(args.carrier, args.cpt, args.icd10, args.denial, args.specialty, args.agent_id)
        if "error" in result:
            print(f"  ✗ Cannot log outcome: {result['error']}")
            sys.exit(1)
        pid = result["patterns"][0]["pattern_id"]
        print(f"\n[Step 3] Logging outcome: {args.approve}")
        oc = get_outcome(pid, args.approve)
        if "error" in oc:
            print(f"  ✗ {oc['error']}")
            sys.exit(1)
        print(f"  ✓ Outcome recorded: {oc['outcome_recorded']}")
        print(f"  new_success_rate: {oc['new_success_rate']}")
        print(f"  new_sample_size: {oc['new_sample_size']}")
        print(f"  is_active: {oc['is_active']}")
        if oc.get("deactivated"):
            print(f"  ⚠ Pattern deactivated (low success rate)")


if __name__ == "__main__":
    main()
