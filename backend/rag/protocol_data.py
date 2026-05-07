"""
Triage protocol knowledge base for Pakistani hospitals.
Adapted from CTAS (Canadian Triage and Acuity Scale) with Pakistani context additions.

Each entry is a protocol chunk that will be embedded and stored in ChromaDB.
The triage agent retrieves the most relevant chunks for each patient complaint.

Structure:
  - id:       unique identifier for the chunk
  - text:     the protocol content (what gets embedded and retrieved)
  - metadata: source, category, level — used for filtering and display
"""

PROTOCOL_CHUNKS = [

    # ── LEVEL 1: RESUSCITATION ────────────────────────────────────────────────
    {
        "id": "L1-001",
        "text": (
            "LEVEL 1 — RESUSCITATION (Immediate, 0 minutes): "
            "Conditions requiring immediate life-saving intervention. "
            "Includes: cardiac arrest, respiratory arrest, unconscious patient not breathing, "
            "severe respiratory distress with oxygen saturation below 85%, "
            "major uncontrolled haemorrhage, severe anaphylaxis with airway compromise, "
            "status epilepticus, severe head injury with unconsciousness. "
            "Action: Call code immediately, do not delay for any assessment."
        ),
        "metadata": {"source": "CTAS-2023", "level": 1, "category": "resuscitation"},
    },
    {
        "id": "L1-002",
        "text": (
            "LEVEL 1 — CARDIAC ARREST PROTOCOL: "
            "Patient found pulseless and not breathing. "
            "Urdu indicators: سانس نہ آنا، نبض نہ ہونا، بے ہوشی (no breathing, no pulse, unconscious). "
            "Immediate CPR, defibrillation if shockable rhythm, IV access, adrenaline 1mg IV every 3-5 minutes. "
            "Pakistani context: heat stroke in summer months can precipitate cardiac arrest — "
            "check for hyperthermia, cool patient aggressively."
        ),
        "metadata": {"source": "CTAS-2023", "level": 1, "category": "cardiac"},
    },
    {
        "id": "L1-003",
        "text": (
            "LEVEL 1 — SEVERE TRAUMA / ROAD TRAFFIC ACCIDENT: "
            "Pakistani context: RTA (road traffic accidents) are the leading cause of Level 1 presentations at PIMS. "
            "Indicators: multiple trauma, penetrating injury to chest/abdomen, GCS below 9, "
            "suspected spinal injury, massive blood loss (clothes soaked), "
            "amputation or near-amputation of limb. "
            "Urdu: گاڑی کا حادثہ، زخم، بہت زیادہ خون (accident, wound, heavy bleeding). "
            "Activate trauma team immediately."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 1, "category": "trauma"},
    },

    # ── LEVEL 2: EMERGENT ─────────────────────────────────────────────────────
    {
        "id": "L2-001",
        "text": (
            "LEVEL 2 — EMERGENT (Within 15 minutes): "
            "High-risk situations that could deteriorate to life-threatening without prompt intervention. "
            "Includes: altered level of consciousness (GCS 9-13), severe chest pain (possible MI), "
            "acute severe asthma, stroke symptoms (facial droop, arm weakness, speech problems), "
            "severe abdominal pain, systolic BP below 90 or above 220, "
            "heart rate above 150 or below 40, severe allergic reaction without airway compromise, "
            "fracture of major bone with neurovascular compromise, active seizure that has stopped."
        ),
        "metadata": {"source": "CTAS-2023", "level": 2, "category": "emergent"},
    },
    {
        "id": "L2-002",
        "text": (
            "LEVEL 2 — CHEST PAIN PROTOCOL: "
            "Any patient over 35 years with chest pain must be triaged as Level 2 minimum. "
            "High-risk features: crushing or pressure-type pain, radiation to left arm or jaw, "
            "associated sweating (diaphoresis), nausea, shortness of breath. "
            "Urdu: سینے میں درد، بائیں بازو میں درد، پسینہ (chest pain, left arm pain, sweating). "
            "Pakistani context: high prevalence of cardiovascular disease; "
            "do not assume musculoskeletal cause in middle-aged patients. "
            "Action: 12-lead ECG within 10 minutes, aspirin 300mg if no contraindication, IV access."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 2, "category": "cardiac"},
    },
    {
        "id": "L2-003",
        "text": (
            "LEVEL 2 — STROKE SYMPTOMS: "
            "Use FAST assessment: Face drooping, Arm weakness, Speech difficulty, Time to call. "
            "Urdu: منہ کا ٹیڑھا ہونا، ہاتھ کا کمزور ہونا، بولنے میں تکلیف (face drooping, arm weak, speech problems). "
            "Any single FAST positive sign in a patient with sudden onset = Level 2. "
            "Time is brain: every minute of delay costs 1.9 million neurons. "
            "Do not give food or water (aspiration risk). "
            "Note time of symptom onset precisely — thrombolysis window is 4.5 hours."
        ),
        "metadata": {"source": "CTAS-2023", "level": 2, "category": "neuro"},
    },
    {
        "id": "L2-004",
        "text": (
            "LEVEL 2 — OBSTETRIC EMERGENCIES: "
            "Pregnant patient with any of: active labour with imminent delivery, "
            "heavy vaginal bleeding (antepartum or postpartum haemorrhage), "
            "severe pre-eclampsia (BP above 160/110 with headache or visual disturbance), "
            "eclamptic seizure, cord prolapse, placental abruption. "
            "Urdu: زچگی، خون آنا، دوروں کا پڑنا (delivery, bleeding, seizures). "
            "Pakistani context: maternal mortality is a priority concern; "
            "obstetric emergencies should never wait in general queue."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 2, "category": "obstetric"},
    },
    {
        "id": "L2-005",
        "text": (
            "LEVEL 2 — ALTERED CONSCIOUSNESS / CONFUSION: "
            "Sudden onset confusion, agitation, or unresponsiveness. "
            "Urdu: بے ہوشی، گھبراہٹ، سمجھ نہ آنا (unconscious, agitated, confused). "
            "Differential includes: hypoglycaemia (check glucose immediately), "
            "meningitis (fever + neck stiffness + photophobia), "
            "drug overdose or poisoning (common in Pakistan — organophosphate, paracetamol, snake bite), "
            "hypertensive encephalopathy, head injury. "
            "Check blood glucose at bedside within 2 minutes."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 2, "category": "neuro"},
    },

    # ── LEVEL 3: URGENT ───────────────────────────────────────────────────────
    {
        "id": "L3-001",
        "text": (
            "LEVEL 3 — URGENT (Within 30 minutes): "
            "Significant symptoms that require timely assessment and treatment. "
            "Includes: moderate abdominal pain, fever above 39C in adults, "
            "moderate respiratory distress (speaking in short sentences, not in distress at rest), "
            "vomiting and diarrhoea with moderate dehydration, "
            "head injury with brief loss of consciousness now fully alert, "
            "musculoskeletal injury with moderate pain, "
            "acute urinary retention, moderate back pain with neurological symptoms."
        ),
        "metadata": {"source": "CTAS-2023", "level": 3, "category": "urgent"},
    },
    {
        "id": "L3-002",
        "text": (
            "LEVEL 3 — FEVER PROTOCOL: "
            "Fever above 38.5C in children under 5 = Level 3 minimum (risk of febrile seizure). "
            "Fever above 39C in adults with rigors or altered appearance = Level 3. "
            "Urdu: بخار، کپکپی، گرم جسم (fever, chills, hot body). "
            "Pakistani context: dengue fever — check for thrombocytopenia risk indicators: "
            "retro-orbital pain, rash, myalgia, bleeding gums. "
            "Malaria should be considered in patients from endemic areas (Balochistan, Sindh rural). "
            "Typhoid: prolonged fever with relative bradycardia and abdominal tenderness."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 3, "category": "infectious"},
    },
    {
        "id": "L3-003",
        "text": (
            "LEVEL 3 — DENGUE FEVER (Pakistani Context): "
            "Dengue is endemic in Pakistan, especially July to November. "
            "Warning signs requiring Level 2 escalation: "
            "abdominal pain or tenderness, persistent vomiting, clinical fluid accumulation, "
            "mucosal bleeding, lethargy, liver enlargement, rising haematocrit with rapid decline in platelet count. "
            "Urdu: ہڈیوں میں درد، آنکھوں کے پیچھے درد، جلد پر دانے (bone pain, retro-orbital pain, rash). "
            "Without warning signs: Level 3. "
            "With any warning sign: escalate to Level 2 immediately."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 3, "category": "infectious"},
    },
    {
        "id": "L3-004",
        "text": (
            "LEVEL 3 — DEHYDRATION ASSESSMENT: "
            "Moderate dehydration (5-10% body weight loss): dry mouth, decreased urine output, "
            "skin turgor mildly reduced, sunken eyes. "
            "Urdu: پیاس، کم پیشاب، کمزوری (thirst, low urine, weakness). "
            "Pakistani context: heat-related dehydration is extremely common in summer months "
            "(April to September). Workers, outdoor labourers, and elderly patients are highest risk. "
            "ORS (oral rehydration salts) should be offered while waiting if patient can swallow. "
            "Severe dehydration (tachycardia, hypotension, confusion) = escalate to Level 2."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 3, "category": "metabolic"},
    },
    {
        "id": "L3-005",
        "text": (
            "LEVEL 3 — HEAT STROKE (Pakistani Context): "
            "Core body temperature above 40C with CNS dysfunction = heat stroke = Level 2. "
            "Heat exhaustion (temperature 37-40C, sweating, weakness, dizziness) = Level 3. "
            "Urdu: گرمی کی وجہ سے بے ہوشی، زیادہ پسینہ، چکر (heat-related unconsciousness, sweating, dizziness). "
            "Peak risk: June to August in Pakistan, outdoor workers, Hajj returnees. "
            "Immediate cooling: remove from heat, cool water sponging, fan, ice packs to neck/axilla/groin. "
            "IV fluids (normal saline) once IV access established."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 3, "category": "environmental"},
    },

    # ── LEVEL 4: LESS URGENT ──────────────────────────────────────────────────
    {
        "id": "L4-001",
        "text": (
            "LEVEL 4 — LESS URGENT (Within 60 minutes): "
            "Symptoms that are distressing but not immediately dangerous. "
            "Includes: chronic condition review with no acute change, "
            "minor trauma without neurovascular compromise, "
            "earache, toothache, urinary tract infection symptoms in otherwise well patients, "
            "mild abdominal pain, skin rash without systemic symptoms, "
            "minor eye complaints (not chemical or penetrating injury), "
            "prescription refill for controlled conditions."
        ),
        "metadata": {"source": "CTAS-2023", "level": 4, "category": "less_urgent"},
    },
    {
        "id": "L4-002",
        "text": (
            "LEVEL 4 — DIABETES MANAGEMENT (Pakistani Context): "
            "Pakistan has one of the highest rates of diabetes in the world. "
            "Hyperglycaemia (blood glucose above 14 mmol/L) without ketones or confusion = Level 4. "
            "Hypoglycaemia (blood glucose below 3.5 mmol/L) = Level 2 (altered consciousness risk). "
            "Urdu: شوگر، ذیابیطس (sugar, diabetes). "
            "Assess: known diabetic?, insulin-dependent?, last medication taken?, "
            "current glucose reading if patient has glucometer."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 4, "category": "metabolic"},
    },

    # ── LEVEL 5: NON-URGENT ───────────────────────────────────────────────────
    {
        "id": "L5-001",
        "text": (
            "LEVEL 5 — NON-URGENT (Within 120 minutes): "
            "Chronic, minor, or administrative presentations. "
            "Includes: minor skin complaints (eczema flare, insect bite without systemic reaction), "
            "prescription refill only (no acute symptoms), "
            "administrative queries (certificates, reports), "
            "cold symptoms without fever or respiratory distress, "
            "chronic pain with no change from baseline, "
            "minor wound for dressing change only."
        ),
        "metadata": {"source": "CTAS-2023", "level": 5, "category": "non_urgent"},
    },

    # ── PAEDIATRIC ADDITIONS ──────────────────────────────────────────────────
    {
        "id": "PED-001",
        "text": (
            "PAEDIATRIC TRIAGE CONSIDERATIONS: "
            "Children under 5 with fever above 38.5C = Level 3 minimum. "
            "Children under 3 months with any fever = Level 2. "
            "Urdu: بچے کو بخار، بچہ رو رہا ہے، بچہ دودھ نہیں پی رہا "
            "(child has fever, child is crying, child not feeding). "
            "Warning signs in children: bulging fontanelle (in infants), "
            "neck stiffness, petechial rash (meningococcal risk), "
            "difficulty breathing (nasal flaring, intercostal recession), "
            "severe dehydration (sunken fontanelle, no tears, no urine for 8+ hours). "
            "Any of these = Level 1 or 2."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 2, "category": "paediatric"},
    },

    # ── PSYCHIATRIC PRESENTATIONS ─────────────────────────────────────────────
    {
        "id": "PSY-001",
        "text": (
            "PSYCHIATRIC TRIAGE GUIDELINES: "
            "Active suicidal ideation with plan and means = Level 2. "
            "Acute psychosis with agitation = Level 2. "
            "Stable psychiatric presentation (medication review, chronic symptoms) = Level 4. "
            "Urdu: خودکشی کے خیالات، ذہنی بیماری، گھبراہٹ (suicidal thoughts, mental illness, agitation). "
            "Pakistani context: psychiatric presentations carry significant stigma. "
            "Use non-stigmatising language. Privacy is essential. "
            "Do not separate psychiatric patients to a visible public waiting area. "
            "Family member presence can be calming and is culturally appropriate."
        ),
        "metadata": {"source": "CTAS-2023-PK", "level": 2, "category": "psychiatric"},
    },

    # ── VITAL SIGN THRESHOLDS ─────────────────────────────────────────────────
    {
        "id": "VITALS-001",
        "text": (
            "VITAL SIGN TRIAGE THRESHOLDS: "
            "Heart rate: below 40 = Level 2, 40-50 = Level 3, 51-100 = normal, 101-130 = Level 3, above 130 = Level 2. "
            "Systolic blood pressure: below 80 = Level 1, 80-90 = Level 2, 91-180 = normal (context-dependent), "
            "181-220 = Level 3, above 220 = Level 2. "
            "Respiratory rate: below 8 = Level 1, 9-11 = Level 2, 12-20 = normal, 21-28 = Level 3, above 28 = Level 2. "
            "Temperature: below 35C = Level 2, 35-37.9 = normal, 38-39 = Level 3, above 39 = Level 2 (adults). "
            "Oxygen saturation: below 85% = Level 1, 85-90% = Level 2, 91-94% = Level 3, 95%+ = normal."
        ),
        "metadata": {"source": "CTAS-2023", "level": None, "category": "vitals"},
    },
]