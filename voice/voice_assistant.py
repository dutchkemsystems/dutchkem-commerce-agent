"""Voice assistant — parse spoken-style commands and text-to-speech hooks."""


try:
    import pyttsx3  # optional TTS engine
except ImportError:  # pragma: no cover
    pyttsx3 = None

COMMAND_MAP = {
    "architecture": ["architecture", "design the system", "plan the system", "architect"],
    "design": ["wireframe", "mockup", "ui design", "ux", "design system", "prototype"],
    "os_kernel": ["kernel", "operating system", "driver", "bootloader", "os module"],
    "game": ["game", "engine", "player", "game dev"],
    "security": ["security", "vulnerability", "scan", "compliance", "audit"],
    "performance": ["performance", "speed", "optimize", "slow"],
    "sdlc": ["sdlc", "lifecycle", "full project", "from requirements"],
    "fleet": ["fleet", "orchestrate", "coordinate", "multiple agents"],
    "general": ["build", "create", "make", "write", "help"],
}


class VoiceAssistant:
    """Parses natural-language/voice input into an intent and handles TTS."""

    def __init__(self, enable_tts: bool = False):
        self.enable_tts = enable_tts and pyttsx3 is not None

    def parse(self, text: str) -> dict:
        lower = text.lower().strip()
        for intent, keywords in COMMAND_MAP.items():
            if any(kw in lower for kw in keywords):
                return {"intent": intent, "raw": text}
        return {"intent": "general", "raw": text}

    def intent_to_command(self, text: str) -> str:
        return f"/{self.parse(text)['intent']}"

    def speak(self, text: str):
        if not self.enable_tts:
            return {"ok": False, "reason": "TTS disabled or pyttsx3 not installed"}
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return {"ok": True}
