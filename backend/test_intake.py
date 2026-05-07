"""
Tests for the patient intake module — updated for frontend field aliases.
Run with: python test_intake.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.intake_model import IntakePayload, AgeGroup, Sex, Language, ConsentPayload
from services.validation import validate_intake
from pydantic import ValidationError as PydanticValidationError

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
results = []

def test(name, condition):
    status = PASS if condition else FAIL
    print(f"{status} | {name}")
    results.append(condition)

print("\n── Original field name tests ──────────────────────────────────────")

# 1. Valid with original field names (age_group + sex)
p = IntakePayload(
    session_id="t-001",
    chief_complaint="سینے میں درد",
    age_group=AgeGroup.adult,
    sex=Sex.male,
    duration="2 ghante se",
    language=Language.urdu,
)
r = validate_intake(p)
test("Original fields: valid payload passes", r.is_valid)
test("Original fields: canonical returned", r.canonical is not None)
test("Original fields: correct age_group", r.canonical.age_group == AgeGroup.adult)
test("Original fields: correct sex", r.canonical.sex == Sex.male)

print("\n── Frontend field alias tests ─────────────────────────────────────")

# 2. Valid with frontend field names (age int + biological_sex string)
p2 = IntakePayload(
    session_id="t-002",
    chief_complaint="Chest pain and difficulty breathing",
    age=20,
    biological_sex="Male",
    duration="2 hours",
    language=Language.english,
    red_flag_symptoms=["Chest pain"],
)
r2 = validate_intake(p2)
test("Frontend aliases: valid payload passes", r2.is_valid)
test("Frontend aliases: age 20 -> adult", r2.canonical.age_group == AgeGroup.adult)
test("Frontend aliases: 'Male' -> Sex.male", r2.canonical.sex == Sex.male)
test("Frontend aliases: red_flag_symptoms stored", r2.canonical.red_flag_symptoms == ["Chest pain"])
test("Frontend aliases: red flags merged into complaint", "Chest pain" in r2.canonical.chief_complaint)

# 3. Age group derivation
for age, expected in [(5, AgeGroup.child), (25, AgeGroup.adult), (65, AgeGroup.elderly)]:
    p_age = IntakePayload(
        session_id=f"t-age-{age}",
        chief_complaint="test complaint",
        age=age,
        biological_sex="Female",
        duration="1 day",
    )
    r_age = validate_intake(p_age)
    test(f"Age {age} derives {expected.value}", r_age.canonical.age_group == expected)

# 4. Female mapping
p_f = IntakePayload(
    session_id="t-003",
    chief_complaint="headache",
    age=30,
    biological_sex="Female",
    duration="3 days",
)
r_f = validate_intake(p_f)
test("'Female' maps to Sex.female", r_f.canonical.sex == Sex.female)

# 5. Multiple red-flag symptoms
p_rf = IntakePayload(
    session_id="t-004",
    chief_complaint="I feel unwell",
    age=45,
    biological_sex="Male",
    duration="1 hour",
    red_flag_symptoms=["Chest pain", "Difficulty breathing", "Loss of consciousness"],
)
r_rf = validate_intake(p_rf)
test("Multiple red flags stored", len(r_rf.canonical.red_flag_symptoms) == 3)
test("Multiple red flags in complaint", "Difficulty breathing" in r_rf.canonical.chief_complaint)

print("\n── Missing field tests ─────────────────────────────────────────────")

# 6. Missing chief_complaint (Pydantic catches at construction)
try:
    IntakePayload(
        session_id="t-005",
        chief_complaint="  ",
        age=20,
        biological_sex="Male",
        duration="1 day",
    )
    test("Blank complaint rejected", False)
except PydanticValidationError:
    test("Blank complaint rejected by Pydantic", True)

# 7. Missing ALL age fields
p_no_age = IntakePayload(
    session_id="t-006",
    chief_complaint="fever",
    duration="1 day",
    language=Language.english,
)
r_no_age = validate_intake(p_no_age)
test("Missing age -> is_valid False", not r_no_age.is_valid)
test("'age' in missing_fields", "age" in r_no_age.missing_fields)

# 8. Missing sex fields
p_no_sex = IntakePayload(
    session_id="t-007",
    chief_complaint="headache",
    age=30,
    duration="2 days",
)
r_no_sex = validate_intake(p_no_sex)
test("Missing sex -> is_valid False", not r_no_sex.is_valid)
test("'sex' in missing_fields", "sex" in r_no_sex.missing_fields)

# 9. Missing duration (Pydantic catches)
try:
    IntakePayload(
        session_id="t-008",
        chief_complaint="cough",
        age=25,
        biological_sex="Male",
        duration="  ",
    )
    test("Blank duration rejected", False)
except PydanticValidationError:
    test("Blank duration rejected by Pydantic", True)

print("\n── Consent tests ───────────────────────────────────────────────────")

c_yes = ConsentPayload(session_id="t-009", consent_given=True)
test("Consent True is valid", c_yes.consent_given is True)

c_no = ConsentPayload(session_id="t-010", consent_given=False)
test("Consent False is valid", c_no.consent_given is False)

# ── Summary ──────────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
print(f"\n── Results: {passed}/{total} passed ───────────────────────────────────\n")
if all(results):
    print("\033[92mAll tests passed!\033[0m\n")
    sys.exit(0)
else:
    print("\033[91mSome tests failed.\033[0m\n")
    sys.exit(1)