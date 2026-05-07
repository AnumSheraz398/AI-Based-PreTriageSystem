import { useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const RED_FLAGS = [
    { key: "chestPain", en: "Chest pain", ur: "سینے میں درد" },
    { key: "breathing", en: "Difficulty breathing", ur: "سانس لینے میں دشواری" },
    { key: "consciousness", en: "Loss of consciousness", ur: "بے ہوشی" },
    { key: "bleeding", en: "Severe bleeding", ur: "شدید خون بہنا" },
];

const SEX_OPTIONS = [
    { value: "male", en: "Male", ur: "مرد" },
    { value: "female", en: "Female", ur: "خاتون" },
    { value: "other", en: "Other", ur: "دیگر" },
    { value: "unknown", en: "Prefer not to say", ur: "بتانا نہیں چاہتے" },
];

function buildValidationPayload(form) {
    return {
        chief_complaint: form.chiefComplaint.trim(),
        age: form.age ? Number(form.age) : null,
        biological_sex: form.biologicalSex,
        duration: form.symptomDuration.trim(),
        red_flag_symptoms: RED_FLAGS.filter((item) => form.redFlags[item.key]).map((item) => item.en),
        language: form.language,
    };
}

function parseValidationResponse(data) {
    // Backend returns: { is_valid: bool, missing_fields: [], message: "", message_ur: "" }
    const complete = Boolean(data?.is_valid);
    const missing = Array.isArray(data?.missing_fields) ? data.missing_fields : [];
    const message = data?.message || "";
    const messageUr = data?.message_ur || "";
    return { complete, missing, message, messageUr };
}

export default function App() {
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);

    const [form, setForm] = useState({
        language: "ur",
        chiefComplaint: "",
        age: "",
        biologicalSex: "",
        symptomDuration: "",
        redFlags: {
            chestPain: false,
            breathing: false,
            consciousness: false,
            bleeding: false,
        },
    });

    const [isRecording, setIsRecording] = useState(false);
    const [recordingError, setRecordingError] = useState("");
    const [sttLoading, setSttLoading] = useState(false);
    const [sttText, setSttText] = useState("");

    const [validationLoading, setValidationLoading] = useState(false);
    const [validationResult, setValidationResult] = useState(null);
    const [validationError, setValidationError] = useState("");

    const [consentLoading, setConsentLoading] = useState(false);
    const [consentStatus, setConsentStatus] = useState("");
    const [consentError, setConsentError] = useState("");

    const sessionId = useMemo(() => {
        if (typeof crypto !== "undefined" && crypto.randomUUID) {
            return crypto.randomUUID();
        }
        return `session-${Date.now()}`;
    }, []);

    const ui = {
        ur: {
            title: "AI پری ٹرائیج انٹیک",
            subtitle: "براہ کرم آواز یا فارم کے ذریعے معلومات فراہم کریں تاکہ فوری رہنمائی ممکن ہو سکے۔",
            voiceTitle: "آواز سے شکایت درج کریں",
            record: "ریکارڈنگ شروع کریں",
            stop: "ریکارڈنگ بند کریں",
            transcribing: "آڈیو ٹرانسکرائب ہو رہا ہے...",
            transcriptionLabel: "موصول شدہ متن",
            validate: "معلومات چیک کریں",
            consentTitle: "رضامندی",
            agree: "میں متفق ہوں",
            disagree: "میں متفق نہیں ہوں",
            language: "زبان",
            intakeTitle: "لازمی معلومات",
        },
        en: {
            title: "AI Pre-Triage Intake",
            subtitle: "Please provide details by voice or form for faster emergency guidance.",
            voiceTitle: "Voice Complaint Capture",
            record: "Start recording",
            stop: "Stop recording",
            transcribing: "Transcribing audio...",
            transcriptionLabel: "Transcribed text",
            validate: "Validate Intake",
            consentTitle: "Consent",
            agree: "I agree",
            disagree: "I don't agree",
            language: "Language",
            intakeTitle: "Mandatory Intake Information",
        },
    }[form.language];

    const isUrdu = form.language === "ur";

    const fieldClass =
        "clinical-input mt-1 w-full rounded-xl border bg-white px-3 py-2 text-slate-800 shadow-sm outline-none transition";

    const setField = (name, value) => {
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const setRedFlag = (key, value) => {
        setForm((prev) => ({
            ...prev,
            redFlags: {
                ...prev.redFlags,
                [key]: value,
            },
        }));
    };

    const startRecording = async () => {
        setRecordingError("");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
            chunksRef.current = [];

            recorder.ondataavailable = (event) => {
                if (event.data?.size > 0) {
                    chunksRef.current.push(event.data);
                }
            };

            recorder.onstop = async () => {
                stream.getTracks().forEach((track) => track.stop());
                const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
                await sendAudioForTranscription(audioBlob);
            };

            mediaRecorderRef.current = recorder;
            recorder.start();
            setIsRecording(true);
        } catch (error) {
            setRecordingError(error?.message || "Microphone access denied.");
        }
    };

    const stopRecording = () => {
        if (!mediaRecorderRef.current) {
            return;
        }
        mediaRecorderRef.current.stop();
        setIsRecording(false);
    };

    const sendAudioForTranscription = async (audioBlob) => {
        setSttLoading(true);
        setSttText("");
        try {
            const formData = new FormData();
            formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);
            formData.append("language", form.language);
            formData.append("session_id", sessionId);

            const response = await fetch(`${API_BASE}/stt/transcribe`, {
                method: "POST",
                body: formData,
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data?.detail || "Unable to transcribe audio.");
            }

            const transcript = data?.urdu_text || data?.transcript || data?.text || "";
            setSttText(transcript);
            if (transcript) {
                setField("chiefComplaint", transcript);
            }
        } catch (error) {
            setRecordingError(error?.message || "STT service failed.");
        } finally {
            setSttLoading(false);
        }
    };

    const validateIntake = async () => {
        setValidationError("");
        setValidationResult(null);
        setValidationLoading(true);

        try {
            const payload = buildValidationPayload(form);
            const response = await fetch(`${API_BASE}/intake/validate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data?.detail || "Validation endpoint returned an error.");
            }

            setValidationResult(parseValidationResponse(data));
        } catch (error) {
            setValidationError(error?.message || "Unable to validate intake fields.");
        } finally {
            setValidationLoading(false);
        }
    };

    const submitConsent = async (agreed) => {
        setConsentError("");
        setConsentLoading(true);
        try {
            const payload = {
                session_id: sessionId,
                consent_given: agreed,
                language: form.language,
                source: "patient-intake",
                captured_at: new Date().toISOString(),
            };

            const response = await fetch(`${API_BASE}/consent`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data?.detail || "Consent endpoint returned an error.");
            }

            setConsentStatus(
                agreed
                    ? form.language === "ur"
                        ? "رضامندی ریکارڈ ہو گئی۔"
                        : "Consent recorded."
                    : form.language === "ur"
                        ? "رضامندی نہیں دی گئی۔ مریض کو دستی ٹرائیج پر بھیج دیں۔"
                        : "Consent refused. Route to manual nurse triage."
            );
            if (data?.message) {
                setConsentStatus(data.message);
            }
        } catch (error) {
            setConsentError(error?.message || "Unable to save consent.");
        } finally {
            setConsentLoading(false);
        }
    };

    return (
        <main className={`intake-shell ${isUrdu ? "locale-ur" : "locale-en"} min-h-screen p-4 md:p-8`} dir={isUrdu ? "rtl" : "ltr"}>
            <section className="intake-panel relative mx-auto max-w-6xl overflow-hidden rounded-3xl p-4 md:p-8">
                <div className="medical-orb medical-orb-top" aria-hidden="true" />
                <div className="medical-orb medical-orb-bottom" aria-hidden="true" />
                <header className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                    <div>
                        <p
                            className={`intake-chip inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${isUrdu ? "tracking-normal" : "uppercase tracking-[0.2em]"
                                }`}
                        >
                            {form.language === "ur" ? "فوری طبی انٹیک" : "Rapid Medical Intake"}
                        </p>
                        <h1 className="intake-title mt-3 text-3xl md:text-5xl">{ui.title}</h1>
                        <p className="mt-2 max-w-2xl text-sm text-slate-700 md:text-base">{ui.subtitle}</p>
                    </div>

                    <div className="language-box w-full rounded-2xl p-3 text-white shadow-lg md:max-w-xs">
                        <label
                            className={`language-label mb-1 block text-xs ${isUrdu ? "tracking-normal" : "uppercase tracking-[0.2em]"
                                }`}
                        >
                            {ui.language}
                        </label>
                        <select
                            className="language-select w-full rounded-xl border p-2"
                            value={form.language}
                            onChange={(event) => setField("language", event.target.value)}
                        >
                            <option value="ur">Urdu</option>
                            <option value="en">English</option>
                        </select>
                    </div>
                </header>

                <div className="grid gap-4 lg:grid-cols-2">
                    <section className="intake-card rounded-2xl p-4 md:p-5">
                        <h2 className="text-xl font-semibold text-slate-900">{ui.voiceTitle}</h2>
                        <p className="endpoint-pill mt-1 inline-flex rounded-full px-2 py-1 text-xs font-semibold tracking-wide">
                            POST /stt/transcribe
                        </p>

                        <div className="mt-4 flex gap-3">
                            {!isRecording ? (
                                <button
                                    type="button"
                                    onClick={startRecording}
                                    className="btn-danger rounded-xl px-4 py-2 text-sm font-medium text-white shadow-md"
                                >
                                    {ui.record}
                                </button>
                            ) : (
                                <button
                                    type="button"
                                    onClick={stopRecording}
                                    className="btn-dark rounded-xl px-4 py-2 text-sm font-medium text-white shadow-md"
                                >
                                    {ui.stop}
                                </button>
                            )}
                            {sttLoading ? <span className="self-center text-sm text-slate-600">{ui.transcribing}</span> : null}
                        </div>

                        {recordingError ? <p className="mt-3 rounded-lg bg-red-100 p-2 text-sm text-red-700">{recordingError}</p> : null}

                        <label className="mt-4 block text-sm font-medium text-slate-800">{ui.transcriptionLabel}</label>
                        <textarea
                            className={`${fieldClass} min-h-24`}
                            value={sttText}
                            onChange={(event) => setSttText(event.target.value)}
                            placeholder={form.language === "ur" ? "ٹرانسکرپٹ یہاں ظاہر ہوگا" : "Transcript appears here"}
                        />
                    </section>

                    <section className="intake-card rounded-2xl p-4 md:p-5">
                        <h2 className="text-xl font-semibold text-slate-900">{ui.intakeTitle}</h2>
                        <p className="endpoint-pill mt-1 inline-flex rounded-full px-2 py-1 text-xs font-semibold tracking-wide">
                            POST /intake/validate
                        </p>

                        <div className="mt-4 grid gap-3">
                            <div>
                                <label className="text-sm font-medium text-slate-800">
                                    {form.language === "ur" ? "بنیادی شکایت" : "Chief complaint"}
                                </label>
                                <textarea
                                    className={fieldClass}
                                    value={form.chiefComplaint}
                                    onChange={(event) => setField("chiefComplaint", event.target.value)}
                                />
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2">
                                <div>
                                    <label className="text-sm font-medium text-slate-800">{form.language === "ur" ? "عمر" : "Age"}</label>
                                    <input
                                        type="number"
                                        min="0"
                                        max="120"
                                        className={fieldClass}
                                        value={form.age}
                                        onChange={(event) => setField("age", event.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="text-sm font-medium text-slate-800">
                                        {form.language === "ur" ? "حیاتیاتی جنس" : "Biological sex"}
                                    </label>
                                    <select
                                        className={fieldClass}
                                        value={form.biologicalSex}
                                        onChange={(event) => setField("biologicalSex", event.target.value)}
                                    >
                                        <option value="">{form.language === "ur" ? "منتخب کریں" : "Select"}</option>
                                        {SEX_OPTIONS.map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {form.language === "ur" ? option.ur : option.en}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="text-sm font-medium text-slate-800">
                                    {form.language === "ur" ? "علامات کا دورانیہ" : "Duration of symptoms"}
                                </label>
                                <input
                                    className={fieldClass}
                                    placeholder={form.language === "ur" ? "مثلاً 2 گھنٹے" : "e.g. 2 hours"}
                                    value={form.symptomDuration}
                                    onChange={(event) => setField("symptomDuration", event.target.value)}
                                />
                            </div>

                            <fieldset className="clinical-fieldset rounded-xl p-3">
                                <legend className="px-2 text-sm font-medium text-slate-800">
                                    {form.language === "ur" ? "خطرے کی علامات" : "Red-flag symptoms"}
                                </legend>
                                <div className="mt-2 grid gap-2">
                                    {RED_FLAGS.map((item) => (
                                        <label key={item.key} className="flex items-center gap-2 text-sm text-slate-700">
                                            <input
                                                type="checkbox"
                                                className="h-4 w-4 rounded border-emerald-300 text-emerald-700 focus:ring-emerald-400"
                                                checked={form.redFlags[item.key]}
                                                onChange={(event) => setRedFlag(item.key, event.target.checked)}
                                            />
                                            {form.language === "ur" ? item.ur : item.en}
                                        </label>
                                    ))}
                                </div>
                            </fieldset>

                            <button
                                type="button"
                                onClick={validateIntake}
                                disabled={validationLoading}
                                className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-md disabled:opacity-60"
                            >
                                {validationLoading
                                    ? form.language === "ur"
                                        ? "چیک ہو رہا ہے..."
                                        : "Validating..."
                                    : ui.validate}
                            </button>
                        </div>

                        {validationError ? <p className="mt-3 rounded-lg bg-red-100 p-2 text-sm text-red-700">{validationError}</p> : null}

                        {validationResult ? (
                            <div
                                className={`mt-3 rounded-lg p-3 text-sm ${validationResult.complete ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"
                                    }`}
                            >
                                {validationResult.complete
                                    ? form.language === "ur"
                                        ? "تمام لازمی معلومات مکمل ہیں۔"
                                        : "All mandatory fields are complete."
                                    : form.language === "ur"
                                        ? `نامکمل فیلڈز: ${validationResult.missing.join(", ") || "نامعلوم"}`
                                        : `Missing fields: ${validationResult.missing.join(", ") || "unknown"}`}
                            </div>
                        ) : null}
                    </section>
                </div>

                <section className="intake-card mt-4 rounded-2xl p-4 md:p-5">
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                            <h2 className="text-xl font-semibold text-slate-900">{ui.consentTitle}</h2>
                            <p className="endpoint-pill mt-1 inline-flex rounded-full px-2 py-1 text-xs font-semibold tracking-wide">
                                POST /consent
                            </p>
                        </div>

                        <div className="flex gap-3">
                            <button
                                type="button"
                                disabled={consentLoading}
                                onClick={() => submitConsent(true)}
                                className="btn-primary rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-md disabled:opacity-60"
                            >
                                {ui.agree}
                            </button>
                            <button
                                type="button"
                                disabled={consentLoading}
                                onClick={() => submitConsent(false)}
                                className="btn-secondary rounded-xl px-4 py-2 text-sm font-semibold text-white shadow-md disabled:opacity-60"
                            >
                                {ui.disagree}
                            </button>
                        </div>
                    </div>

                    <p className="mt-3 text-sm text-slate-700">
                        {form.language === "ur"
                            ? "میں تصدیق کرتا/کرتی ہوں کہ میری معلومات AI پری ٹرائیج کے لئے استعمال کی جا سکتی ہیں۔"
                            : "I confirm that my information can be used for AI-assisted pre-triage."}
                    </p>

                    {consentError ? <p className="mt-2 rounded-lg bg-red-100 p-2 text-sm text-red-700">{consentError}</p> : null}
                    {consentStatus ? <p className="mt-2 rounded-lg bg-sky-100 p-2 text-sm text-sky-900">{consentStatus}</p> : null}
                </section>
            </section>
        </main>
    );
}
