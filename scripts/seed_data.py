import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def make_patient(name, age, symptoms, language="ur"):
    pid = str(uuid4())
    return {
        "id": pid,
        "patient_name": name,
        "age": age,
        "symptoms": symptoms,
        "language": language,
        "created_at": datetime.utcnow().isoformat(),
    }


def main() -> None:
    patients = [
        make_patient("Ali Khan", 42, ["fever", "cough"]),
        make_patient("Ayesha Noor", 67, ["chest pain", "breathlessness"]),
        make_patient("Hamza Ahmed", 26, ["leg injury"]),
    ]

    triage_logs = [
        {
            "patient_id": patients[0]["id"],
            "urgency_level": 3,
            "department": "General Medicine",
            "reasoning": "Moderate symptoms",
        },
        {
            "patient_id": patients[1]["id"],
            "urgency_level": 5,
            "department": "Emergency",
            "reasoning": "Hard safety rule triggered",
        },
    ]

    out_dir = Path("scripts") / "seed_output"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "patients.json").write_text(json.dumps(patients, indent=2), encoding="utf-8")
    (out_dir / "triage_logs.json").write_text(json.dumps(triage_logs, indent=2), encoding="utf-8")

    print(f"Wrote dummy seed files to: {out_dir}")


if __name__ == "__main__":
    main()
