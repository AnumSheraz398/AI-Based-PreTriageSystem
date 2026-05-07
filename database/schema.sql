CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY,
    patient_name VARCHAR(120) NOT NULL,
    age INT NOT NULL CHECK (age >= 0 AND age <= 120),
    gender VARCHAR(20),
    symptoms TEXT NOT NULL,
    language VARCHAR(5) NOT NULL DEFAULT 'ur',
    input_mode VARCHAR(10) NOT NULL DEFAULT 'text',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS triage_logs (
    id BIGSERIAL PRIMARY KEY,
    patient_id UUID NOT NULL,
    urgency_level INT NOT NULL CHECK (urgency_level BETWEEN 1 AND 5),
    department VARCHAR(80) NOT NULL,
    reasoning TEXT NOT NULL,
    protocol_chunks JSONB NOT NULL,
    safety_override_applied BOOLEAN NOT NULL DEFAULT FALSE,
    triaged_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_triage_patient
        FOREIGN KEY(patient_id)
        REFERENCES patients(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    actor VARCHAR(50) NOT NULL DEFAULT 'system',
    payload JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triage_patient_id ON triage_logs(patient_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_patients_created_at ON patients(created_at);
