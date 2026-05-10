/**
 * ResultScreen.jsx
 * 
 * Patient result screen — shown after consent is granted and POST /route completes.
 * 
 * HOW TO USE IN YOUR APP:
 * 1. Copy this file into: frontend/kiosk-ui/src/components/ResultScreen.jsx
 * 2. In your main App.jsx, after consent "I agree" is clicked:
 *    - Call POST /route with the canonical intake object
 *    - Pass the response to this component
 * 
 * Props:
 *   routeData   — the full response from POST /route
 *   language    — "ur" or "en"
 *   onNewPatient — callback to reset the entire form for next patient
 */

import { useState, useEffect } from "react";

// ── Urgency level config ──────────────────────────────────────────────────────
const LEVEL_CONFIG = {
  1: {
    bg:       "#FFF0F0",
    border:   "#FF3B3B",
    badge:    "#FF3B3B",
    icon:     "🚨",
    label_en: "IMMEDIATE EMERGENCY",
    label_ur: "فوری ایمرجنسی",
  },
  2: {
    bg:       "#FFF5EB",
    border:   "#FF8C00",
    badge:    "#FF8C00",
    icon:     "⚡",
    label_en: "URGENT",
    label_ur: "فوری توجہ",
  },
  3: {
    bg:       "#FFFDE7",
    border:   "#FFD600",
    badge:    "#B8860B",
    icon:     "⏱",
    label_en: "SEE SOON",
    label_ur: "جلد دیکھا جائے",
  },
  4: {
    bg:       "#F1F8E9",
    border:   "#4CAF50",
    badge:    "#2E7D32",
    icon:     "✓",
    label_en: "LESS URGENT",
    label_ur: "کم فوری",
  },
  5: {
    bg:       "#E3F2FD",
    border:   "#90CAF9",
    badge:    "#1565C0",
    icon:     "○",
    label_en: "NON-URGENT",
    label_ur: "غیر فوری",
  },
};

// ── Loading screen ────────────────────────────────────────────────────────────
export function LoadingScreen({ language }) {
  const isUrdu = language === "ur";
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(d => d.length >= 3 ? "." : d + ".");
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={styles.loadingWrap}>
      <div style={styles.loadingCard}>
        {/* Spinner */}
        <div style={styles.spinnerWrap}>
          <div style={styles.spinner} />
        </div>
        <p style={{ ...styles.loadingTitle, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu
            ? `آپ کی معلومات جانچی جا رہی ہیں${dots}`
            : `Checking your information${dots}`}
        </p>
        <p style={{ ...styles.loadingSubtitle, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu
            ? "براہ کرم انتظار کریں — AI جائزہ لے رہا ہے"
            : "Please wait — AI is reviewing your case"}
        </p>
      </div>

      {/* CSS keyframe animation via style tag */}
      <style>{`
        @keyframes spin {
          0%   { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.6; }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-10px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        .result-row {
          animation: slideIn 0.4s ease forwards;
        }
      `}</style>
    </div>
  );
}

// ── Error screen ──────────────────────────────────────────────────────────────
export function ErrorScreen({ language, onRetry, onCallNurse }) {
  const isUrdu = language === "ur";
  return (
    <div style={styles.errorWrap}>
      <div style={styles.errorCard}>
        <div style={styles.errorIcon}>⚠</div>
        <h2 style={{ ...styles.errorTitle, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu ? "ایک مسئلہ پیش آیا" : "Something went wrong"}
        </h2>
        <p style={{ ...styles.errorMsg, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu
            ? "سسٹم عارضی طور پر دستیاب نہیں۔ براہ کرم نرس کو بلائیں یا دوبارہ کوشش کریں۔"
            : "The system is temporarily unavailable. Please call a nurse or try again."}
        </p>
        <div style={styles.errorButtons}>
          <button style={styles.retryBtn} onClick={onRetry}>
            {isUrdu ? "دوبارہ کوشش کریں" : "Try Again"}
          </button>
          <button style={styles.nurseBtn} onClick={onCallNurse}>
            {isUrdu ? "نرس کو بلائیں" : "Call Nurse"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Nurse queue screen (consent declined) ─────────────────────────────────────
export function NurseQueueScreen({ language, onNewPatient }) {
  const isUrdu = language === "ur";
  return (
    <div style={styles.nurseWrap}>
      <div style={styles.nurseCard}>
        <div style={styles.nurseIcon}>🏥</div>
        <h2 style={{ ...styles.nurseTitle, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu ? "نرس جلد آپ سے ملیں گی" : "A nurse will see you shortly"}
        </h2>
        <p style={{ ...styles.nurseMsg, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu
            ? "براہ کرم انتظار گاہ میں بیٹھ جائیں۔ نرس آپ کا نام پکاریں گی۔"
            : "Please take a seat in the waiting area. A nurse will call your name."}
        </p>
        <div style={styles.nurseSeats}>
          <span style={{ fontSize: 32 }}>🪑 🪑 🪑</span>
        </div>
        <button style={styles.newPatientBtn} onClick={onNewPatient}>
          {isUrdu ? "اگلا مریض" : "Next Patient"}
        </button>
      </div>
    </div>
  );
}

// ── Main result screen ────────────────────────────────────────────────────────
export default function ResultScreen({ routeData, language, onNewPatient }) {
  const isUrdu = language === "ur";
  const level  = routeData?.level || 3;
  const config = LEVEL_CONFIG[level] || LEVEL_CONFIG[3];
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Trigger animation on mount
    setTimeout(() => setVisible(true), 50);

    // For Level 1 — play alert sound
    if (level === 1) {
      try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(880, ctx.currentTime);
        osc.frequency.setValueAtTime(440, ctx.currentTime + 0.3);
        osc.frequency.setValueAtTime(880, ctx.currentTime + 0.6);
        gain.gain.setValueAtTime(0.5, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 1.2);
      } catch (e) {
        // Audio not supported — silent fail
      }
    }
  }, [level]);

  return (
    <div style={{
      ...styles.wrap,
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(16px)",
      transition: "opacity 0.5s ease, transform 0.5s ease",
    }}>

      {/* Level 1 emergency flash banner */}
      {level === 1 && (
        <div style={styles.emergencyBanner}>
          <span style={{ animation: "pulse 1s infinite" }}>
            🚨 {isUrdu ? "فوری ایمرجنسی — عملے کو آگاہ کر دیا گیا ہے" : "IMMEDIATE EMERGENCY — Staff have been alerted"} 🚨
          </span>
        </div>
      )}

      {/* Main card */}
      <div style={{
        ...styles.card,
        background:   config.bg,
        borderColor:  config.border,
        borderWidth:  level <= 2 ? 3 : 1.5,
      }}>

        {/* Token number */}
        <div style={styles.tokenSection}>
          <div style={styles.tokenLabel}>
            {isUrdu ? "آپ کا نمبر" : "Your token number"}
          </div>
          <div style={{ ...styles.tokenNumber, color: config.border }}>
            {routeData?.token_number || "---"}
          </div>
        </div>

        {/* Urgency badge */}
        <div style={{ ...styles.badge, background: config.badge }}>
          <span style={styles.badgeIcon}>{config.icon}</span>
          <span style={styles.badgeText}>
            {isUrdu ? config.label_ur : config.label_en}
          </span>
          <span style={styles.badgeLevel}>
            {isUrdu ? `درجہ ${level}` : `Level ${level}`}
          </span>
        </div>

        {/* Main patient message */}
        <div style={{ ...styles.messageBox, direction: isUrdu ? "rtl" : "ltr" }}>
          <p style={styles.messageText}>
            {isUrdu
              ? routeData?.patient_message_ur
              : routeData?.patient_message_en}
          </p>
        </div>

        {/* Info rows */}
        <div style={styles.infoGrid}>

          {/* Department */}
          <div className="result-row" style={{ ...styles.infoRow, animationDelay: "0.1s" }}>
            <span style={styles.infoIcon}>🏥</span>
            <div style={{ direction: isUrdu ? "rtl" : "ltr", flex: 1 }}>
              <div style={styles.infoLabel}>
                {isUrdu ? "شعبہ" : "Department"}
              </div>
              <div style={styles.infoValue}>
                {isUrdu
                  ? routeData?.department_name_ur
                  : routeData?.department_name_en}
              </div>
            </div>
          </div>

          {/* Location */}
          <div className="result-row" style={{ ...styles.infoRow, animationDelay: "0.2s" }}>
            <span style={styles.infoIcon}>📍</span>
            <div style={{ direction: isUrdu ? "rtl" : "ltr", flex: 1 }}>
              <div style={styles.infoLabel}>
                {isUrdu ? "جانے کا راستہ" : "Where to go"}
              </div>
              <div style={styles.infoValue}>
                {isUrdu
                  ? routeData?.location_ur
                  : routeData?.location_en}
              </div>
            </div>
          </div>

          {/* Wait time */}
          {routeData?.wait_mins > 0 && (
            <div className="result-row" style={{ ...styles.infoRow, animationDelay: "0.3s" }}>
              <span style={styles.infoIcon}>⏳</span>
              <div style={{ direction: isUrdu ? "rtl" : "ltr", flex: 1 }}>
                <div style={styles.infoLabel}>
                  {isUrdu ? "تخمینی انتظار" : "Estimated wait"}
                </div>
                <div style={styles.infoValue}>
                  {isUrdu
                    ? `تقریباً ${routeData?.wait_mins} منٹ`
                    : `Approximately ${routeData?.wait_mins} minutes`}
                </div>
              </div>
            </div>
          )}

          {/* Requires review badge */}
          {routeData?.requires_review && (
            <div style={styles.reviewWarning}>
              {isUrdu
                ? "⚠ نرس کا جائزہ ضروری ہے"
                : "⚠ Nurse review required"}
            </div>
          )}
        </div>

        {/* Explanation (longer LLM-generated text) */}
        {(routeData?.explanation_ur || routeData?.explanation_en) && (
          <div style={{ ...styles.explanationBox, direction: isUrdu ? "rtl" : "ltr" }}>
            <p style={styles.explanationText}>
              {isUrdu
                ? routeData?.explanation_ur
                : routeData?.explanation_en}
            </p>
          </div>
        )}

        {/* New patient button */}
        <button style={styles.newPatientBtn} onClick={onNewPatient}>
          {isUrdu ? "اگلا مریض شروع کریں" : "Start Next Patient"}
        </button>

      </div>

      {/* CSS animations */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.5; }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(-10px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        .result-row {
          animation: slideIn 0.4s ease forwards;
        }
      `}</style>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const styles = {
  // Loading
  loadingWrap: {
    display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "60vh", padding: "2rem",
  },
  loadingCard: {
    background: "white", borderRadius: 20, padding: "3rem 2rem",
    textAlign: "center", boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    maxWidth: 420, width: "100%",
  },
  spinnerWrap: { display: "flex", justifyContent: "center", marginBottom: 24 },
  spinner: {
    width: 56, height: 56,
    border: "4px solid #E0F0E9",
    borderTop: "4px solid #0F6E56",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  loadingTitle: {
    fontSize: 20, fontWeight: 600, color: "#1A1A1A", marginBottom: 8,
  },
  loadingSubtitle: {
    fontSize: 15, color: "#666",
  },

  // Error
  errorWrap: {
    display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "60vh", padding: "2rem",
  },
  errorCard: {
    background: "white", borderRadius: 20, padding: "2.5rem",
    textAlign: "center", boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    maxWidth: 420, width: "100%", border: "2px solid #FFD0D0",
  },
  errorIcon: { fontSize: 48, marginBottom: 16 },
  errorTitle: { fontSize: 22, fontWeight: 700, color: "#CC0000", marginBottom: 12 },
  errorMsg: { fontSize: 15, color: "#555", lineHeight: 1.6, marginBottom: 24 },
  errorButtons: { display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" },
  retryBtn: {
    background: "#0F6E56", color: "white", border: "none",
    borderRadius: 12, padding: "12px 24px", fontSize: 16,
    fontWeight: 600, cursor: "pointer",
  },
  nurseBtn: {
    background: "white", color: "#0F6E56",
    border: "2px solid #0F6E56",
    borderRadius: 12, padding: "12px 24px", fontSize: 16,
    fontWeight: 600, cursor: "pointer",
  },

  // Nurse queue
  nurseWrap: {
    display: "flex", alignItems: "center", justifyContent: "center",
    minHeight: "60vh", padding: "2rem",
  },
  nurseCard: {
    background: "white", borderRadius: 20, padding: "3rem 2rem",
    textAlign: "center", boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    maxWidth: 420, width: "100%", border: "2px solid #B0D0C8",
  },
  nurseIcon: { fontSize: 56, marginBottom: 20 },
  nurseTitle: { fontSize: 24, fontWeight: 700, color: "#085041", marginBottom: 12 },
  nurseMsg: { fontSize: 16, color: "#444", lineHeight: 1.6, marginBottom: 24 },
  nurseSeats: { marginBottom: 24 },

  // Result screen
  wrap: {
    padding: "1rem",
    maxWidth: 560,
    margin: "0 auto",
  },
  emergencyBanner: {
    background: "#FF3B3B", color: "white",
    padding: "14px 20px", borderRadius: 12,
    fontSize: 16, fontWeight: 700,
    textAlign: "center", marginBottom: 16,
  },
  card: {
    borderRadius: 20, border: "2px solid",
    padding: "1.5rem", boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    display: "flex", flexDirection: "column", gap: 16,
  },

  // Token
  tokenSection: { textAlign: "center", paddingBottom: 8 },
  tokenLabel: {
    fontSize: 13, fontWeight: 500, color: "#888",
    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4,
  },
  tokenNumber: {
    fontSize: 48, fontWeight: 800, letterSpacing: "-0.02em",
    lineHeight: 1,
  },

  // Badge
  badge: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "10px 16px", borderRadius: 12,
    color: "white",
  },
  badgeIcon: { fontSize: 20 },
  badgeText: { fontSize: 16, fontWeight: 700, flex: 1 },
  badgeLevel: { fontSize: 13, opacity: 0.85 },

  // Message
  messageBox: {
    background: "rgba(255,255,255,0.7)",
    borderRadius: 12, padding: "14px 16px",
  },
  messageText: {
    fontSize: 17, color: "#1A1A1A", lineHeight: 1.6, margin: 0,
    fontWeight: 500,
  },

  // Info rows
  infoGrid: { display: "flex", flexDirection: "column", gap: 10 },
  infoRow: {
    display: "flex", alignItems: "flex-start", gap: 12,
    background: "rgba(255,255,255,0.7)",
    borderRadius: 12, padding: "12px 14px",
  },
  infoIcon: { fontSize: 22, flexShrink: 0 },
  infoLabel: {
    fontSize: 11, fontWeight: 600, color: "#888",
    textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2,
  },
  infoValue: { fontSize: 15, fontWeight: 500, color: "#1A1A1A", lineHeight: 1.4 },

  reviewWarning: {
    background: "#FFF3CD", border: "1px solid #FFD700",
    borderRadius: 10, padding: "10px 14px",
    fontSize: 14, fontWeight: 600, color: "#856404",
    textAlign: "center",
  },

  // Explanation
  explanationBox: {
    background: "rgba(255,255,255,0.6)",
    borderRadius: 12, padding: "14px 16px",
    borderLeft: "3px solid rgba(0,0,0,0.1)",
  },
  explanationText: {
    fontSize: 14, color: "#444", lineHeight: 1.7, margin: 0,
  },

  // Button
  newPatientBtn: {
    width: "100%", background: "#0F6E56", color: "white",
    border: "none", borderRadius: 14, padding: "16px",
    fontSize: 17, fontWeight: 700, cursor: "pointer",
    marginTop: 4, letterSpacing: "0.01em",
  },
};