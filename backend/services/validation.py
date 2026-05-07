from models.intake_model import IntakePayload, CanonicalIntake, ValidationResult, AgeGroup, Sex
import logging

logger = logging.getLogger(__name__)

MANDATORY_FIELDS = {
    "chief_complaint": ("Chief complaint",    "مریض کی تکلیف"),
    "age":             ("Age",                "عمر"),
    "sex":             ("Sex",                "جنس"),
    "duration":        ("Duration",           "کتنے عرصے سے"),
}

URDU_MESSAGES = {
    "valid":          "آپ کی معلومات مکمل ہیں۔ ابھی AI جائزہ لے رہا ہے۔",
    "missing_fields": "کچھ ضروری معلومات ابھی باقی ہیں۔ براہ کرم مکمل کریں۔",
    "invalid_data":   "کچھ معلومات درست نہیں۔ براہ کرم دوبارہ کوشش کریں۔",
}

ENGLISH_MESSAGES = {
    "valid":          "Information complete. AI is reviewing your case.",
    "missing_fields": "Some required information is missing. Please complete all fields.",
    "invalid_data":   "Some information appears invalid. Please try again.",
}


def validate_intake(payload: IntakePayload) -> ValidationResult:
    """
    Validate mandatory fields, resolving frontend aliases (age, biological_sex).
    Returns a clean CanonicalIntake on success or a list of missing fields on failure.
    """
    missing: list[str] = []

    # Chief complaint
    if not payload.chief_complaint or len(payload.chief_complaint.strip()) < 2:
        missing.append("chief_complaint")

    # Age — accept age_group OR age OR age_exact
    has_age = (
        payload.age_group is not None
        or payload.age is not None
        or payload.age_exact is not None
    )
    if not has_age:
        missing.append("age")

    # Sex — accept sex OR biological_sex
    has_sex = payload.sex is not None or bool(payload.biological_sex)
    if not has_sex:
        missing.append("sex")

    # Duration
    if not payload.duration or not payload.duration.strip():
        missing.append("duration")

    if missing:
        missing_en = [MANDATORY_FIELDS.get(f, (f, f))[0] for f in missing]
        missing_ur = [MANDATORY_FIELDS.get(f, (f, f))[1] for f in missing]
        logger.info(f"Validation FAILED | session={payload.session_id} | missing={missing}")
        return ValidationResult(
            session_id=payload.session_id,
            is_valid=False,
            missing_fields=missing,
            canonical=None,
            message=f"{ENGLISH_MESSAGES['missing_fields']} Missing: {', '.join(missing_en)}",
            message_ur=f"{URDU_MESSAGES['missing_fields']} ناقص: {', '.join(missing_ur)}",
        )

    # Resolve aliased fields
    resolved_age_group = payload.resolve_age_group()
    resolved_sex = payload.resolve_sex()

    # Merge red_flag_symptoms into chief_complaint context if present
    complaint = payload.chief_complaint.strip()
    if payload.red_flag_symptoms:
        flags = ", ".join(payload.red_flag_symptoms)
        complaint = f"{complaint} [Red-flag symptoms: {flags}]"

    canonical = CanonicalIntake(
        session_id=payload.session_id,
        chief_complaint=complaint,
        age_group=resolved_age_group,
        sex=resolved_sex,
        duration=payload.duration.strip(),
        language=payload.language,
        age_exact=payload.age if payload.age is not None else payload.age_exact,
        red_flag_symptoms=payload.red_flag_symptoms,
        chronic_conditions=payload.chronic_conditions,
        current_medications=payload.current_medications,
        mr_number=payload.mr_number,
        transcript=payload.transcript,
        consent_given=False,
    )

    logger.info(f"Validation OK | session={payload.session_id} | age_group={resolved_age_group} | sex={resolved_sex}")
    return ValidationResult(
        session_id=payload.session_id,
        is_valid=True,
        missing_fields=[],
        canonical=canonical,
        message=ENGLISH_MESSAGES["valid"],
        message_ur=URDU_MESSAGES["valid"],
    )