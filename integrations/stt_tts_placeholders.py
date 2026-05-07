def simulate_stt(audio_blob: bytes) -> str:
    # Placeholder for Urdu/English speech-to-text.
    if not audio_blob:
        return ""
    return "simulated transcription text"

def simulate_tts(text: str, language: str = "ur") -> bytes:
    # Placeholder for text-to-speech output bytes.
    if not text:
        return b""
    return f"[simulated-{language}-audio]{text}".encode("utf-8")
