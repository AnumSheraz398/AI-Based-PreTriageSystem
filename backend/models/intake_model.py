from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import uuid


class AgeGroup(str, Enum):
    child   = "child"      # under 12
    adult   = "adult"      # 12-59
    elderly = "elderly"    # 60+


class Sex(str, Enum):
    male              = "male"
    female            = "female"
    prefer_not_to_say = "prefer_not_to_say"


class Language(str, Enum):
    urdu    = "ur"
    english = "en"


def _new_session_id() -> str:
    return str(uuid.uuid4())


class IntakePayload(BaseModel):
    """
    Accepts the exact payload the frontend sends:
      - session_id        optional (auto-generated if missing)
      - age               int  (derives age_group automatically)
      - biological_sex    str  "Male" / "Female"  (maps to Sex enum)
      - red_flag_symptoms list[str]  (checkbox values)
    Original field names (age_group, sex) also still work.
    """

    # session_id is optional — backend auto-generates if frontend omits it
    session_id: str = Field(
        default_factory=_new_session_id,
        description="Session ID — auto-generated if not provided"
    )

    # ── Complaint — mandatory ─────────────────────────────────────────────────
    chief_complaint: str = Field(..., min_length=2, max_length=1000)

    # ── Age — accept int from frontend OR enum from original API ──────────────
    age:       Optional[int]      = Field(None, ge=0, le=120)
    age_group: Optional[AgeGroup] = Field(None)
    age_exact: Optional[int]      = Field(None, ge=0, le=120)

    # ── Sex — accept "Male"/"Female" string OR enum ───────────────────────────
    biological_sex: Optional[str] = Field(None)   # "Male", "Female", "Other"
    sex:            Optional[Sex] = Field(None)

    # ── Duration — mandatory ──────────────────────────────────────────────────
    duration: str = Field(..., min_length=1, max_length=200)

    # ── Language — default English (matches frontend default) ────────────────
    language: Language = Field(default=Language.english)

    # ── Red-flag symptoms — list of checkbox labels ───────────────────────────
    red_flag_symptoms: Optional[List[str]] = Field(default=None)

    # ── Optional extras ───────────────────────────────────────────────────────
    chronic_conditions:  Optional[str] = Field(None, max_length=500)
    current_medications: Optional[str] = Field(None, max_length=500)
    mr_number:           Optional[str] = Field(None, max_length=50)
    transcript:          Optional[str] = Field(None)

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("chief_complaint")
    @classmethod
    def complaint_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Chief complaint cannot be blank")
        return v.strip()

    @field_validator("duration")
    @classmethod
    def duration_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Duration cannot be blank")
        return v.strip()

    # ── Resolver helpers ──────────────────────────────────────────────────────
    def resolve_age_group(self) -> AgeGroup:
        """Derive AgeGroup from age int if age_group not directly provided."""
        if self.age_group:
            return self.age_group
        raw = self.age if self.age is not None else self.age_exact
        if raw is None:
            return AgeGroup.adult      # safe default
        if raw < 12:
            return AgeGroup.child
        if raw >= 60:
            return AgeGroup.elderly
        return AgeGroup.adult

    def resolve_sex(self) -> Sex:
        """Normalise biological_sex string to Sex enum."""
        if self.sex:
            return self.sex
        if self.biological_sex:
            mapping = {
                "male":              Sex.male,
                "female":            Sex.female,
                "prefer not to say": Sex.prefer_not_to_say,
                "other":             Sex.prefer_not_to_say,
            }
            return mapping.get(self.biological_sex.lower(), Sex.prefer_not_to_say)
        return Sex.prefer_not_to_say


# ── Validated canonical model ─────────────────────────────────────────────────
class CanonicalIntake(BaseModel):
    session_id:          str
    chief_complaint:     str
    age_group:           AgeGroup
    sex:                 Sex
    duration:            str
    language:            Language
    age_exact:           Optional[int]       = None
    red_flag_symptoms:   Optional[List[str]] = None
    chronic_conditions:  Optional[str]       = None
    current_medications: Optional[str]       = None
    mr_number:           Optional[str]       = None
    transcript:          Optional[str]       = None
    consent_given:       bool                = False


# ── Consent payload ───────────────────────────────────────────────────────────
class ConsentPayload(BaseModel):
    session_id:    str
    consent_given: bool
    language:      Language = Language.urdu


# ── STT response ──────────────────────────────────────────────────────────────
class STTResponse(BaseModel):
    session_id:        str
    transcript:        str
    language_detected: str
    confidence:        Optional[float] = None


# ── Validation result ─────────────────────────────────────────────────────────
class ValidationResult(BaseModel):
    session_id:     str
    is_valid:       bool
    missing_fields: List[str]
    canonical:      Optional[CanonicalIntake] = None
    message:        str
    message_ur:     str