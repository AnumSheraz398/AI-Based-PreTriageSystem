/**
 * DisclaimerBanner.jsx
 * 
 * Legal/safety disclaimer banner for the portfolio demo.
 * Shows once per browser session as a modal, then collapses into a
 * small permanent footer note so the warning is always visible.
 * 
 * HOW TO USE:
 * 1. Copy into: frontend/kiosk-ui/src/components/DisclaimerBanner.jsx
 *    AND        frontend/staff-dashboard/src/components/DisclaimerBanner.jsx
 * 2. Import and render at the very top of your App.jsx, before everything else:
 * 
 *    import DisclaimerBanner from "./components/DisclaimerBanner";
 *    
 *    export default function App() {
 *      return (
 *        <>
 *          <DisclaimerBanner language={form.language} />
 *          <main>...</main>
 *        </>
 *      );
 *    }
 */

import { useState, useEffect } from "react";

export default function DisclaimerBanner({ language = "en" }) {
  const isUrdu = language === "ur";
  const [dismissed, setDismissed] = useState(true); // default hidden until check runs

  useEffect(() => {
    const seen = sessionStorage.getItem("pretriage_disclaimer_seen");
    setDismissed(seen === "true");
  }, []);

  const handleDismiss = () => {
    sessionStorage.setItem("pretriage_disclaimer_seen", "true");
    setDismissed(true);
  };

  if (dismissed) {
    return <PersistentFooterNote isUrdu={isUrdu} />;
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.card}>
        <div style={styles.iconRow}>
          <span style={styles.icon}>⚠</span>
        </div>

        <h2 style={{ ...styles.title, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu ? "اہم نوٹس" : "Important Notice"}
        </h2>

        <p style={{ ...styles.body, direction: isUrdu ? "rtl" : "ltr" }}>
          {isUrdu
            ? "یہ ایپلیکیشن AI انجینئرنگ کی مہارت ظاہر کرنے کے لیے ایک پورٹ فولیو پراجیکٹ ہے۔ یہ کوئی طبی آلہ نہیں ہے اور اسے حقیقی طبی تشخیص یا ایمرجنسی فیصلہ سازی کے لیے استعمال نہیں کیا جانا چاہیے۔ ہمیشہ مستند طبی ماہرین سے رجوع کریں۔"
            : "This application is a portfolio project for demonstrating AI engineering skills. It is not a medical device and must not be used for real clinical diagnosis or emergency decision-making. Always consult qualified healthcare professionals."}
        </p>

        <button style={styles.button} onClick={handleDismiss}>
          {isUrdu ? "میں سمجھ گیا" : "I Understand"}
        </button>
      </div>
    </div>
  );
}

function PersistentFooterNote({ isUrdu }) {
  return (
    <div style={{ ...styles.footerNote, direction: isUrdu ? "rtl" : "ltr" }}>
      <span style={styles.footerIcon}>⚠</span>
      <span>
        {isUrdu
          ? "پورٹ فولیو ڈیمو — طبی استعمال کے لیے نہیں۔ یہ آلہ تشخیص یا ایمرجنسی فیصلوں کا متبادل نہیں۔"
          : "Portfolio demo — not for medical use. This tool does not replace professional diagnosis or emergency care."}
      </span>
    </div>
  );
}

const styles = {
  overlay: {
    position: "fixed",
    top: 0, left: 0, right: 0, bottom: 0,
    background: "rgba(0,0,0,0.55)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
    padding: "1.5rem",
  },
  card: {
    background: "white",
    borderRadius: 20,
    padding: "2rem 1.75rem",
    maxWidth: 460,
    width: "100%",
    boxShadow: "0 8px 40px rgba(0,0,0,0.25)",
    border: "2px solid #FFD27A",
    textAlign: "center",
  },
  iconRow: { marginBottom: 12 },
  icon: {
    fontSize: 40,
    display: "inline-flex",
    width: 64, height: 64,
    alignItems: "center", justifyContent: "center",
    background: "#FFF3D6",
    borderRadius: "50%",
  },
  title: {
    fontSize: 22, fontWeight: 700, color: "#1A1A1A",
    margin: "12px 0 14px",
  },
  body: {
    fontSize: 15, color: "#444", lineHeight: 1.7,
    margin: "0 0 22px",
  },
  button: {
    background: "#0F6E56", color: "white",
    border: "none", borderRadius: 12,
    padding: "13px 32px", fontSize: 16, fontWeight: 700,
    cursor: "pointer", width: "100%",
  },
  footerNote: {
    background: "#FFF8E8",
    borderBottom: "1px solid #FFE2A8",
    color: "#7A5A00",
    fontSize: 12.5,
    padding: "8px 16px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    textAlign: "center",
    lineHeight: 1.4,
  },
  footerIcon: { fontSize: 14, flexShrink: 0 },
};
