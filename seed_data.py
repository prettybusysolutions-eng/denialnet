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

    # ── Additional 30 patterns (total 50) ────────────────────────────────────
    # D0220 — Intraoral periapical first film
    {
        "carrier": "Cigna Dental", "cpt_code": "D0220", "icd10_code": "Z01.818",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not covered as separate procedure",
        "resolution_steps": ["Reclassify as part of comprehensive exam if done same visit", "Submit with D0150 and note as diagnostic", "If standalone: add narrative for specific tooth issue"],
        "attachments_required": ["clinical_notes", "xray"], "resubmission_format": "ADA form",
        "success_rate": 0.72, "sample_size": 41, "contributor_id": "system-seed"
    },
    {
        "carrier": "Delta Dental", "cpt_code": "D0220", "icd10_code": "Z01.818",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Frequency limitation exceeded",
        "resolution_steps": ["Confirm no prior same-tooth X-ray in past 12 months", "Document medical necessity for repeat imaging", "Submit with progression notes"],
        "attachments_required": ["prior_xray", "clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.83, "sample_size": 56, "contributor_id": "system-seed"
    },
    # D0330 — Panoramic film
    {
        "carrier": "Aetna Dental", "cpt_code": "D0330", "icd10_code": "Z01.818",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not a covered benefit",
        "resolution_steps": ["Confirm if patient is new or has specific diagnostic need", "Reclassify as D0210 (full mouth series) if more comprehensive", "Submit with orthodontic or surgical justification"],
        "attachments_required": ["treatment_plan", "clinical_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.59, "sample_size": 22, "contributor_id": "system-seed"
    },
    # D2140 — Amalgam one surface primary
    {
        "carrier": "MetLife Dental", "cpt_code": "D2140", "icd10_code": "K02.51",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Composite alternative preferred",
        "resolution_steps": ["Add narrative: 'Amalgam requested due to moisture control challenges'", "Document patient-specific factor (e.g., parafunctional habit)", "Reference ADA position on material selection"],
        "attachments_required": ["clinical_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.64, "sample_size": 28, "contributor_id": "system-seed"
    },
    # D2950 — Core buildup
    {
        "carrier": "Delta Dental", "cpt_code": "D2950", "icd10_code": "K08.52",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not medically necessary",
        "resolution_steps": ["Include pre-op photo showing insufficient coronal structure", "Document need for crown retention", "Reference crown lengthening vs core buildup criteria"],
        "attachments_required": ["preop_photo", "clinical_notes", "xray"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.78, "sample_size": 37, "contributor_id": "system-seed"
    },
    {
        "carrier": "Guardian Dental", "cpt_code": "D2950", "icd10_code": "K08.52",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Missing tooth structure documentation",
        "resolution_steps": ["Submit X-ray showing <50% coronal structure remaining", "Include core material and technique", "Note crown lengthening was not alternative"],
        "attachments_required": ["xray", "clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.81, "sample_size": 44, "contributor_id": "system-seed"
    },
    # D3310 — Root canal anterior
    {
        "carrier": "Cigna Dental", "cpt_code": "D3310", "icd10_code": "K04.01",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Tooth not restorable",
        "resolution_steps": ["Submit current X-ray showing root integrity", "Document periodontal support", "Include treatment plan for final restoration"],
        "attachments_required": ["periapical_xray", "periodontal_charting", "treatment_plan"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.69, "sample_size": 31, "contributor_id": "system-seed"
    },
    {
        "carrier": "Delta Dental", "cpt_code": "D3310", "icd10_code": "K04.01",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Pre-authorization required",
        "resolution_steps": ["Submit retroactive PA with all required documentation", "Include diagnostic images", "Document reason for emergency vs planned treatment"],
        "attachments_required": ["xray_series", "clinical_notes"], "resubmission_format": "ADA form + retroactive PA",
        "success_rate": 0.85, "sample_size": 53, "contributor_id": "system-seed"
    },
    # D3320 — Root canal bicuspid
    {
        "carrier": "MetLife Dental", "cpt_code": "D3320", "icd10_code": "K04.02",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Tooth already extracted",
        "resolution_steps": ["Confirm tooth number — resubmit with correct tooth designation", "If extraction occurred: bill D7111 (extraction) instead", "Include documentation of extraction date"],
        "attachments_required": ["xray", "extraction_note"], "resubmission_format": "ADA form",
        "success_rate": 0.74, "sample_size": 26, "contributor_id": "system-seed"
    },
    # D3330 — Root canal molar
    {
        "carrier": "Aetna Dental", "cpt_code": "D3330", "icd10_code": "K04.03",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Specialty fee applies",
        "resolution_steps": ["Confirm if treating dentist is in-network specialist", "If GP: note why specialist was not used", "Submit with endodontic diagnosis"],
        "attachments_required": ["endodontic_diagnosis", "xray"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.62, "sample_size": 19, "contributor_id": "system-seed"
    },
    {
        "carrier": "United Healthcare Dental", "cpt_code": "D3330", "icd10_code": "K04.03",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Medical necessity not established",
        "resolution_steps": ["Submit all diagnostic films showing pulp necrosis", "Document failed conservative treatment", "Include periapical pathology"],
        "attachments_required": ["full_xray_series", "clinical_notes", "prior_treatment"], "resubmission_format": "ADA form + medical necessity letter",
        "success_rate": 0.76, "sample_size": 35, "contributor_id": "system-seed"
    },
    # D4240 — Gingival flap procedure
    {
        "carrier": "Delta Dental", "cpt_code": "D4240", "icd10_code": "K05.31",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not covered under periodontal benefit",
        "resolution_steps": ["Confirm active periodontal disease with charting", "Document failed SRP in prior 12 months", "Submit with AAP classification and treatment plan"],
        "attachments_required": ["periodontal_charting", "prior_srp", "xray"], "resubmission_format": "EDI + surgical narrative",
        "success_rate": 0.71, "sample_size": 29, "contributor_id": "system-seed"
    },
    # D4270 — Pedicle soft tissue graft
    {
        "carrier": "Guardian Dental", "cpt_code": "D4270", "icd10_code": "K06.010",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Experimental/investigational",
        "resolution_steps": ["Document gingival recession classification (RT1-RT3)", "Submit evidence-based criteria for procedure", "Reference AAP guidelines on soft tissue grafting"],
        "attachments_required": ["clinical_photos", "periodontal_charting", "treatment_plan"], "resubmission_format": "ADA form + appeal letter",
        "success_rate": 0.55, "sample_size": 16, "contributor_id": "system-seed"
    },
    # D4910 — Periodontal maintenance
    {
        "carrier": "Delta Dental", "cpt_code": "D4910", "icd10_code": "Z96.5",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not within global period",
        "resolution_steps": ["Verify date of active periodontal treatment", "If within 12 months of SRP/surgery: attach original treatment records", "If outside global: document separate benefit"],
        "attachments_required": ["prior_treatment_records", "periodontal_charting"], "resubmission_format": "ADA form",
        "success_rate": 0.88, "sample_size": 62, "contributor_id": "system-seed"
    },
    {
        "carrier": "Cigna Dental", "cpt_code": "D4910", "icd10_code": "Z96.5",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "No history of active periodontal therapy",
        "resolution_steps": ["Submit documentation of prior periodontal surgery or SRP", "If new patient: document comprehensive periodontal evaluation", "Include periodontal charting from initial visit"],
        "attachments_required": ["periodontal_charting", "prior_treatment"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.73, "sample_size": 38, "contributor_id": "system-seed"
    },
    # D5110/D5120 — Complete denture
    {
        "carrier": "MetLife Dental", "cpt_code": "D5110", "icd10_code": "Z97.2",
        "specialty": "Prosthodontics", "geography": "TX",
        "denial_reason": "Waiting period not met",
        "resolution_steps": ["Verify waiting period completion date", "If due to employment change: note HIPAA portability", "Submit with proof of prior coverage"],
        "attachments_required": ["prior_coverage_letter"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.67, "sample_size": 24, "contributor_id": "system-seed"
    },
    # D5640 — Replace broken tooth on denture
    {
        "carrier": "Delta Dental", "cpt_code": "D5640", "icd10_code": "Z97.2",
        "specialty": "Prosthodontics", "geography": "TX",
        "denial_reason": "Part of denture repair benefit only",
        "resolution_steps": ["Confirm this is tooth replacement, not repair", "If repair: resubmit as D5520 (replace broken tooth)", "If new tooth addition: document structural need"],
        "attachments_required": ["denture_photo", "clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.79, "sample_size": 32, "contributor_id": "system-seed"
    },
    # D6240 — Pontic porcelain fused to high noble
    {
        "carrier": "Aetna Dental", "cpt_code": "D6240", "icd10_code": "K08.119",
        "specialty": "Prosthodontics", "geography": "TX",
        "denial_reason": "Porcelain not covered for posterior",
        "resolution_steps": ["Change to metal-ceramic or metal-only for posterior", "If anterior: document visible location in smile zone", "Submit with bridge placement plan"],
        "attachments_required": ["xray", "clinical_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.61, "sample_size": 18, "contributor_id": "system-seed"
    },
    # D6750 — Crown porcelain fused to high noble
    {
        "carrier": "Cigna Dental", "cpt_code": "D6750", "icd10_code": "K08.121",
        "specialty": "Prosthodontics", "geography": "TX",
        "denial_reason": "Metal crown preferred",
        "resolution_steps": ["Document patient allergy to base metals", "Submit dermatology or allergy testing", "If no allergy: switch to PFM or full-cast"],
        "attachments_required": ["allergy_test", "clinical_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.58, "sample_size": 21, "contributor_id": "system-seed"
    },
    {
        "carrier": "Delta Dental", "cpt_code": "D6750", "icd10_code": "K08.121",
        "specialty": "Prosthodontics", "geography": "TX",
        "denial_reason": "Already had crown on same tooth",
        "resolution_steps": ["Confirm if replacement vs original crown claim", "Submit date of original crown placement", "Document reason for replacement (fracture, decay, fit issue)"],
        "attachments_required": ["prior_crown_records", "current_xray"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.82, "sample_size": 47, "contributor_id": "system-seed"
    },
    # D7140 — Extraction erupted tooth
    {
        "carrier": "United Healthcare Dental", "cpt_code": "D7140", "icd10_code": "K08.109",
        "specialty": "Oral Surgery", "geography": "TX",
        "denial_reason": "Wrong procedure code",
        "resolution_steps": ["Verify if surgical vs routine extraction needed", "If surgical (D7210): document elevation or sectioning required", "If routine: confirm uncomplicated extraction"],
        "attachments_required": ["xray", "clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.90, "sample_size": 71, "contributor_id": "system-seed"
    },
    # D7230 — Extraction impacted tooth
    {
        "carrier": "Guardian Dental", "cpt_code": "D7230", "icd10_code": "K01.0",
        "specialty": "Oral Surgery", "geography": "TX",
        "denial_reason": "Not medically necessary",
        "resolution_steps": ["Document impaction type (horizontal, vertical, mesioangular)", "Submit panoramic X-ray showing impaction position", "Include oral surgery consultation notes"],
        "attachments_required": ["panoramic_xray", "surgical_consult", "clinical_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.86, "sample_size": 58, "contributor_id": "system-seed"
    },
    # D7999 — Unspecified oral surgery
    {
        "carrier": "MetLife Dental", "cpt_code": "D7999", "icd10_code": "Z90.89",
        "specialty": "Oral Surgery", "geography": "TX",
        "denial_reason": "Unlisted procedure requires predetermination",
        "resolution_steps": ["Submit detailed narrative describing procedure", "Include diagram or photo if applicable", "Reference similar established procedure codes if possible"],
        "attachments_required": ["surgical_narrative", "diagram_or_photo"], "resubmission_format": "ADA form + predetermination request",
        "success_rate": 0.51, "sample_size": 15, "contributor_id": "system-seed"
    },
    # D9110 — Palliative treatment
    {
        "carrier": "Aetna Dental", "cpt_code": "D9110", "icd10_code": "K08.90",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not covered as emergency visit",
        "resolution_steps": ["Add diagnosis of acute condition requiring palliative care", "Document tooth-specific diagnosis (not just pain)", "Submit emergency visit notes"],
        "attachments_required": ["emergency_notes", "xray"], "resubmission_format": "ADA form",
        "success_rate": 0.77, "sample_size": 39, "contributor_id": "system-seed"
    },
    # D9440 — Office visit after hours
    {
        "carrier": "Delta Dental", "cpt_code": "D9440", "icd10_code": "Z00.00",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Not a covered benefit",
        "resolution_steps": ["Confirm if plan covers after-hours emergencies", "Document medical necessity for after-hours visit", "If not covered: collect patient portion upfront"],
        "attachments_required": ["after_hours_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.44, "sample_size": 12, "contributor_id": "system-seed"
    },
    # D0460 — Pulp vitality test
    {
        "carrier": "Cigna Dental", "cpt_code": "D0460", "icd10_code": "K04.00",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Diagnostic service not covered",
        "resolution_steps": ["Reclassify as part of exam or emergency service", "Document what it was part of (comprehensive exam, root canal eval)", "Submit with supporting procedures"],
        "attachments_required": ["clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.69, "sample_size": 27, "contributor_id": "system-seed"
    },
    # D0470 — Diagnostic models
    {
        "carrier": "MetLife Dental", "cpt_code": "D0470", "icd10_code": "Z01.818",
        "specialty": "Orthodontics", "geography": "TX",
        "denial_reason": "Requires prior authorization",
        "resolution_steps": ["Submit predetermination with study models", "Include treatment plan and diagnostic findings", "Document why models are necessary for treatment"],
        "attachments_required": ["treatment_plan", "diagnostic_findings"], "resubmission_format": "ADA form + PA",
        "success_rate": 0.75, "sample_size": 34, "contributor_id": "system-seed"
    },
    # D1510 — Space maintainer fixed unilateral
    {
        "carrier": "Delta Dental", "cpt_code": "D1510", "icd10_code": "Z98.890",
        "specialty": "Pediatric Dentistry", "geography": "TX",
        "denial_reason": "Patient over age limit",
        "resolution_steps": ["Confirm patient age at time of extraction", "Document early loss of primary tooth", "Submit with extraction date and reason"],
        "attachments_required": ["extraction_record", "patient_dob"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.66, "sample_size": 23, "contributor_id": "system-seed"
    },
    # D1515 — Space maintainer fixed bilateral
    {
        "carrier": "Guardian Dental", "cpt_code": "D1515", "icd10_code": "Z98.890",
        "specialty": "Pediatric Dentistry", "geography": "TX",
        "denial_reason": "Not medically necessary",
        "resolution_steps": ["Document space analysis showing arch length insufficiency", "Submit with panoramic X-ray", "Reference AAPD guidelines on space maintenance"],
        "attachments_required": ["space_analysis", "panoramic_xray", "treatment_plan"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.71, "sample_size": 30, "contributor_id": "system-seed"
    },
    # D9930 — Treatment of complications (post-surgery)
    {
        "carrier": "United Healthcare Dental", "cpt_code": "D9930", "icd10_code": "T81.89",
        "specialty": "Oral Surgery", "geography": "TX",
        "denial_reason": "Not separate from global surgery",
        "resolution_steps": ["Confirm this is separate complication, not normal post-op", "Document specific complication requiring additional treatment", "Submit within 30-day global period"],
        "attachments_required": ["complication_notes", "postop_notes"], "resubmission_format": "ADA form + appeal",
        "success_rate": 0.63, "sample_size": 20, "contributor_id": "system-seed"
    },
    # D0350 — 2D oral cavity image
    {
        "carrier": "Aetna Dental", "cpt_code": "D0350", "icd10_code": "Z01.818",
        "specialty": "Dental", "geography": "TX",
        "denial_reason": "Duplicate with D0250",
        "resolution_steps": ["Confirm D0250 (extraoral) vs D0350 (intraoral) distinction", "If intraoral: resubmit as D0350 with clinical justification", "If extraoral: use D0250"],
        "attachments_required": ["clinical_notes"], "resubmission_format": "ADA form",
        "success_rate": 0.80, "sample_size": 45, "contributor_id": "system-seed"
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
