"""Seed data — 20 high-frequency dental denial patterns."""
from database import get_session, init_db
from models import Pattern, AgentBalance
import uuid

SEED_PATTERNS = [
    # ── D2740 — Crown ───────────────────────────────────────────────────────
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
        "success_rate": 0.89,
        "sample_size": 67,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "Cigna Dental",
        "cpt_code": "D2740",
        "icd10_code": "K02.9",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not medically necessary",
        "resolution_steps": [
            "Include narrative: 'Tooth has >50% decay involving dentin, unable to restore with filling'",
            "Attach pre-treatment photos",
            "Reference ADA criteria for crowns"
        ],
        "attachments_required": ["xray", "clinical_notes", "photos"],
        "resubmission_format": "EDI + narrative attachment",
        "success_rate": 0.82,
        "sample_size": 43,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "MetLife Dental",
        "cpt_code": "D2740",
        "icd10_code": "K02.9",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Missing narrative",
        "resolution_steps": [
            "Add narrative: 'Crown needed due to extensive caries destroying >2/3 of coronal structure'",
            "Include tooth number and surface involvement",
            "Reference policy section for major restoration"
        ],
        "attachments_required": ["clinical_notes"],
        "resubmission_format": "ADA form + memo",
        "success_rate": 0.91,
        "sample_size": 55,
        "contributor_id": "system-seed"
    },
    # ── D2335 — Composite Anterior ─────────────────────────────────────────
    {
        "carrier": "Delta Dental",
        "cpt_code": "D2335",
        "icd10_code": "K02.3",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Wrong surface billed",
        "resolution_steps": [
            "Review clinical notes for surfaces treated",
            "Correct surface code to match documentation",
            "Resubmit with surface breakdown"
        ],
        "attachments_required": ["clinical_notes"],
        "resubmission_format": "ADA form",
        "success_rate": 0.76,
        "sample_size": 29,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "Aetna Dental",
        "cpt_code": "D2335",
        "icd10_code": "K02.3",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Frequency limitation exceeded",
        "resolution_steps": [
            "Check patient's claim history for prior same-surface restoration",
            "If billing replacement: note 'replacement of failed restoration' and include date of original",
            "Submit with narrative explaining clinical necessity"
        ],
        "attachments_required": ["clinical_notes", "prior_xray"],
        "resubmission_format": "ADA form + appeal letter",
        "success_rate": 0.68,
        "sample_size": 38,
        "contributor_id": "system-seed"
    },
    # ── D0150 — Comprehensive Oral Exam ─────────────────────────────────────
    {
        "carrier": "United Healthcare Dental",
        "cpt_code": "D0150",
        "icd10_code": "Z00.00",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not covered under plan",
        "resolution_steps": [
            "Verify plan documents for exam coverage",
            "If on preventive plan: re-file under D0120 (periodic oral exam)",
            "Add patient responsibility disclaimer if not covered"
        ],
        "attachments_required": [],
        "resubmission_format": "ADA form",
        "success_rate": 0.71,
        "sample_size": 51,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "Guardian Dental",
        "cpt_code": "D0150",
        "icd10_code": "Z00.00",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Missing documentation",
        "resolution_steps": [
            "Attach comprehensive exam form with findings",
            "Include periodontal charting",
            "Document medical necessity for comprehensive vs periodic"
        ],
        "attachments_required": ["periodontal_charting", "exam_form"],
        "resubmission_format": "ADA form + attachments",
        "success_rate": 0.84,
        "sample_size": 31,
        "contributor_id": "system-seed"
    },
    # ── D4341 — Periodontal Scaling ─────────────────────────────────────────
    {
        "carrier": "Delta Dental",
        "cpt_code": "D4341",
        "icd10_code": "K05.30",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not authorized",
        "resolution_steps": [
            "Submit prior authorization with periodontal charting",
            "Include pocket depth measurements (4mm or greater)",
            "Document radiographic evidence of bone loss"
        ],
        "attachments_required": ["periodontal_charting", "xray"],
        "resubmission_format": "EDI + PA form",
        "success_rate": 0.79,
        "sample_size": 44,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "Cigna Dental",
        "cpt_code": "D4341",
        "icd10_code": "K05.30",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not medically necessary",
        "resolution_steps": [
            "Add narrative with CAL measurements and bleeding indices",
            "Reference AAP guidelines for SRP criteria",
            "Include full-mouth X-ray series showing bone levels"
        ],
        "attachments_required": ["full_mouth_xray", "periodontal_charting", "clinical_notes"],
        "resubmission_format": "EDI + narrative",
        "success_rate": 0.73,
        "sample_size": 36,
        "contributor_id": "system-seed"
    },
    # ── D7210 — Extraction Erupted Tooth ────────────────────────────────────
    {
        "carrier": "MetLife Dental",
        "cpt_code": "D7210",
        "icd10_code": "K08.109",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Missing diagnosis code",
        "resolution_steps": [
            "Add ICD-10: K08.109 (unspecified disorder of teeth)",
            "Verify tooth number matches clinical record",
            "Include extraction narrative"
        ],
        "attachments_required": ["clinical_notes"],
        "resubmission_format": "ADA form",
        "success_rate": 0.93,
        "sample_size": 82,
        "contributor_id": "system-seed"
    },
    {
        "carrier": "Aetna Dental",
        "cpt_code": "D7210",
        "icd10_code": "K08.109",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Tooth not in same arch",
        "resolution_steps": [
            "Verify tooth number and arch billed",
            "Correct to opposing arch if needed",
            "Add narrative for complex extraction reason"
        ],
        "attachments_required": ["xray"],
        "resubmission_format": "ADA form",
        "success_rate": 0.67,
        "sample_size": 22,
        "contributor_id": "system-seed"
    },
    # ── D2391 — Composite Posterior ────────────────────────────────────────
    {
        "carrier": "Delta Dental",
        "cpt_code": "D2391",
        "icd10_code": "K02.52",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Amalgam vs composite conflict",
        "resolution_steps": [
            "Verify plan prefers amalgam in posterior",
            "Submit with narrative: 'Patient preference + clinical indication for composite'",
            "Reference ADA statement on restorative material choice"
        ],
        "attachments_required": ["clinical_notes"],
        "resubmission_format": "ADA form + appeal",
        "success_rate": 0.61,
        "sample_size": 19,
        "contributor_id": "system-seed"
    },
    # ── D9222 — Deep Sedation ───────────────────────────────────────────────
    {
        "carrier": "Cigna Dental",
        "cpt_code": "D9222",
        "icd10_code": "K00.00",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not pre-authorized",
        "resolution_steps": [
            "Submit retroactive PA with medical history justifying sedation",
            "Document ASA classification",
            "Include procedure notes for the surgical procedure requiring sedation"
        ],
        "attachments_required": ["medical_history", "procedure_notes", "asa_classification"],
        "resubmission_format": "ADA form + PA",
        "success_rate": 0.58,
        "sample_size": 17,
        "contributor_id": "system-seed"
    },
    # ── D8680 — Orthodontic Retention ───────────────────────────────────────
    {
        "carrier": "Delta Dental",
        "cpt_code": "D8680",
        "icd10_code": "Z46.9",
        "specialty": "Orthodontic",
        "geography": "TX",
        "denial_reason": "Orthodontic benefit exhausted",
        "resolution_steps": [
            "Verify lifetime orthodontic maximum",
            "If treatment plan changed: resubmit with new treatment dates",
            "Submit adjustment period as separate from active treatment"
        ],
        "attachments_required": ["treatment_plan"],
        "resubmission_format": "ADA form",
        "success_rate": 0.72,
        "sample_size": 28,
        "contributor_id": "system-seed"
    },
    # ── D4260 — Osseous Surgery ─────────────────────────────────────────────
    {
        "carrier": "MetLife Dental",
        "cpt_code": "D4260",
        "icd10_code": "K05.40",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not covered under periodontal benefit",
        "resolution_steps": [
            "Confirm patient's periodontal benefit is active",
            "Submit with full periodontal charting",
            "Document failed conservative therapy (SRP results)"
        ],
        "attachments_required": ["periodontal_charting", "prior_srp_notes", "xray"],
        "resubmission_format": "EDI + surgical narrative",
        "success_rate": 0.66,
        "sample_size": 23,
        "contributor_id": "system-seed"
    },
    # ── D1555 — Re-cement or re-bond fixed retainer ──────────────────────────
    {
        "carrier": "Guardian Dental",
        "cpt_code": "D1555",
        "icd10_code": "Z48.812",
        "specialty": "Orthodontic",
        "geography": "TX",
        "denial_reason": "Frequency limitation",
        "resolution_steps": [
            "Check time since last re-cement",
            "Submit with note: 'Orthodontic fixed retainer debonded due to normal wear'",
            "Include photo of debonded retainer"
        ],
        "attachments_required": ["clinical_notes", "photo"],
        "resubmission_format": "ADA form",
        "success_rate": 0.88,
        "sample_size": 41,
        "contributor_id": "system-seed"
    },
    # ── D1354 — Interim Caries Arresting Medicament ──────────────────────────
    {
        "carrier": "United Healthcare Dental",
        "cpt_code": "D1354",
        "icd10_code": "K02.9",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not covered procedure",
        "resolution_steps": [
            "Confirm plan exclusions for preventive medicament",
            "If medically necessary for high-risk patient: submit with Silver Diamine Fluoride documentation",
            "Reclassify as D1351 (sealant) if applicable"
        ],
        "attachments_required": ["clinical_notes", "caries_risk_assessment"],
        "resubmission_format": "ADA form + appeal",
        "success_rate": 0.54,
        "sample_size": 14,
        "contributor_id": "system-seed"
    },
    # ── D4910 — Periodontal Maintenance ─────────────────────────────────────
    {
        "carrier": "Aetna Dental",
        "cpt_code": "D4910",
        "icd10_code": "Z96.5",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Not within 90 days of surgery",
        "resolution_steps": [
            "Verify SRP or osseous surgery date",
            "If within global period: no separate billing allowed",
            "If after global: document and resubmit with surgery date"
        ],
        "attachments_required": ["periodontal_charting", "surgery_date"],
        "resubmission_format": "ADA form",
        "success_rate": 0.81,
        "sample_size": 49,
        "contributor_id": "system-seed"
    },
    # ── D0250 — Extraoral 2D photographic image ──────────────────────────────
    {
        "carrier": "Cigna Dental",
        "cpt_code": "D0250",
        "icd10_code": "Z01.818",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Diagnostic benefit not applicable",
        "resolution_steps": [
            "Reclassify as D0350 (2D oral cavity image) if intraoral",
            "If extraoral required for ortho: submit with ortho treatment notes",
            "Reference ADA D0350 vs D0250 distinction"
        ],
        "attachments_required": ["clinical_notes"],
        "resubmission_format": "ADA form",
        "success_rate": 0.63,
        "sample_size": 21,
        "contributor_id": "system-seed"
    },
    # ── D6080 — Implant maintenance ──────────────────────────────────────────
    {
        "carrier": "Delta Dental",
        "cpt_code": "D6080",
        "icd10_code": "Z96.5",
        "specialty": "Dental",
        "geography": "TX",
        "denial_reason": "Implant not documented",
        "resolution_steps": [
            "Submit implant placement date and location",
            "Include implant manufacturer and type",
            "Document implant success and health of surrounding tissue"
        ],
        "attachments_required": ["implant_documentation", "periapical_xray"],
        "resubmission_format": "ADA form + implant info",
        "success_rate": 0.77,
        "sample_size": 33,
        "contributor_id": "system-seed"
    },
]


def seed():
    init_db()
    session = get_session()
    try:
        # Check if already seeded
        existing = session.query(Pattern).filter_by(contributor_id="system-seed").count()
        if existing >= len(SEED_PATTERNS):
            print(f"Already seeded ({existing} patterns). Skipping.")
            return

        for p in SEED_PATTERNS:
            pattern = Pattern(**p)
            session.add(pattern)

        # Seed agent with starting credits
        for agent_id in ["aurex", "buyer-agent-001", "buyer-agent-002"]:
            existing_bal = session.query(AgentBalance).filter_by(agent_id=agent_id).first()
            if not existing_bal:
                bal = AgentBalance(agent_id=agent_id, balance_cents=5000)  # $50 each
                session.add(bal)

        session.commit()
        print(f"Seeded {len(SEED_PATTERNS)} patterns + starting credits.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
