"""
Voice Controller — Industry-Standard Architecture
=================================================
Always-on background listening (like Siri / Google Assistant):

  • listen_in_background()   — callback-based, zero-gap, no blocking timeout
  • Tuned energy/pause params — snappy endpoint detection (<0.5 s silence)
  • Intent matching via word-sets — handles natural variation
  • Word-to-number conversion   — "slide five" → 5
  • TTS in a dedicated daemon thread — never blocks listening
  • `status` property for HUD display

Wake word: "computer"
"""

from __future__ import annotations

import re
import queue
import threading
from typing import Optional

import speech_recognition as sr

# ── Optional TTS ───────────────────────────────────────────────────────────────
try:
    import pyttsx3
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False

# ── Word-number table ──────────────────────────────────────────────────────────
_WORD_NUMS: dict[str, int] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
    "twenty one": 21, "twenty two": 22, "twenty three": 23,
    "twenty four": 24, "twenty five": 25, "twenty six": 26,
    "twenty seven": 27, "twenty eight": 28, "twenty nine": 29,
    "thirty": 30,
}

WAKE_WORD = "computer"

# ── Intent word-sets ───────────────────────────────────────────────────────────
_NEXT_WORDS    = {"next", "forward", "advance", "ahead"}
_PREV_WORDS    = {"previous", "back", "backward", "before", "prior", "last"}
_SPOT_WORDS    = {"spotlight", "spot", "light", "highlight"}
_ZOOM_WORDS    = {"zoom", "magnify", "magnifier", "loupe", "enlarge"}
_QUIT_WORDS    = {"exit", "quit", "end", "stop", "close", "bye"}
_GOTO_WORDS    = {"go", "jump", "slide", "open", "show", "goto", "navigate"}


def _extract_number(text: str) -> Optional[int]:
    """Pull the first number (digit or word) from *text*, or None."""
    # Try digit first
    m = re.search(r"\b(\d+)\b", text)
    if m:
        return int(m.group(1))
    # Try multi-word numbers (longest match first)
    for phrase in sorted(_WORD_NUMS, key=len, reverse=True):
        if phrase in text:
            return _WORD_NUMS[phrase]
    return None


class VoiceController:
    """
    Background-listening voice controller.

    Parameters
    ----------
    cmd_queue    : queue.Queue  — engine drains this each frame
    total_slides : int          — used for bounds-checking goto commands
    """

    # Public status values the engine can read for HUD
    STATUS_STARTING    = "starting"
    STATUS_READY       = "ready"
    STATUS_PROCESSING  = "processing"
    STATUS_STOPPED     = "stopped"

    def __init__(self, cmd_queue: queue.Queue, total_slides: int):
        self.q            = cmd_queue
        self.total_slides = total_slides

        # Recognizer — tuned for fast, responsive transcription
        self.r = sr.Recognizer()
        self.r.pause_threshold          = 0.5   # end-of-speech after 0.5 s silence
        self.r.phrase_threshold         = 0.1   # begin phrase quickly
        self.r.non_speaking_duration    = 0.3   # minimum silence between phrases
        self.r.dynamic_energy_threshold = True  # auto-adjust for room noise
        self.r.energy_threshold         = 300   # starting baseline

        self._bg_listener   = None              # returned by listen_in_background
        self._tts_queue     = queue.Queue()     # TTS jobs for the speaker thread
        self._tts_thread    = None
        self._stop_event    = threading.Event()
        self._status        = self.STATUS_STOPPED
        self._status_lock   = threading.Lock()

        # TTS engine (lives only in the TTS thread)
        self._tts_available = _TTS_AVAILABLE

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def status(self) -> str:
        with self._status_lock:
            return self._status

    def start(self):
        """Initialise mic, calibrate, and start always-on background listening."""
        self._stop_event.clear()
        self._set_status(self.STATUS_STARTING)

        # Start TTS thread first so feedback is available immediately
        if self._tts_available:
            self._tts_thread = threading.Thread(
                target=self._tts_loop, daemon=True, name="VoiceTTS"
            )
            self._tts_thread.start()

        # Calibrate and launch background listener in a setup thread
        # (calibration blocks ~1 s — don't freeze the engine startup)
        threading.Thread(
            target=self._start_background_listener, daemon=True, name="VoiceSetup"
        ).start()

    def stop(self):
        """Stop background listening and TTS."""
        self._stop_event.set()
        self._set_status(self.STATUS_STOPPED)
        if self._bg_listener:
            try:
                self._bg_listener(wait_for_stop=False)
            except Exception:
                pass
            self._bg_listener = None
        # Poison-pill the TTS queue
        self._tts_queue.put(None)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _set_status(self, s: str):
        with self._status_lock:
            self._status = s

    def _start_background_listener(self):
        try:
            with sr.Microphone() as source:
                print("[voice] Calibrating for ambient noise (1 s)…")
                self.r.adjust_for_ambient_noise(source, duration=1)
                print(f"[voice] Energy threshold set to {self.r.energy_threshold:.0f}")

            # listen_in_background returns a stopper callable
            self._bg_listener = self.r.listen_in_background(
                sr.Microphone(),
                self._audio_callback,
                phrase_time_limit=6,   # cap each audio chunk at 6 s
            )
            self._set_status(self.STATUS_READY)
            print(f"[voice] Always-on. Wake word: '{WAKE_WORD}'")

        except Exception as e:
            print(f"[voice] Microphone setup failed: {e}")
            self._set_status(self.STATUS_STOPPED)

    def _audio_callback(self, recognizer: sr.Recognizer, audio: sr.AudioData):
        """
        Called by the background thread for every phrase detected.
        Must return quickly — heavy work dispatched inline (Google API is fast).
        """
        if self._stop_event.is_set():
            return

        self._set_status(self.STATUS_PROCESSING)
        try:
            text = recognizer.recognize_google(audio).lower().strip()
            print(f"[voice] Heard: '{text}'")
            cmd = self._parse(text)
            if cmd:
                self.q.put(cmd)
        except sr.UnknownValueError:
            pass  # couldn't decode audio
        except sr.RequestError as e:
            print(f"[voice] Google API error: {e}")
        except Exception as e:
            print(f"[voice] Callback error: {e}")
        finally:
            if not self._stop_event.is_set():
                self._set_status(self.STATUS_READY)

    # ── Intent parser ─────────────────────────────────────────────────────────

    def _parse(self, text: str) -> Optional[str]:
        """
        Return a command token if the wake word is present; else None.
        Uses word-set intent matching — not fragile exact-string tests.
        """
        if WAKE_WORD not in text:
            return None

        # Strip everything up to and including the wake word
        body = text[text.index(WAKE_WORD) + len(WAKE_WORD):].strip()
        words = set(body.split())

        # ── Next ──────────────────────────────────────────────────────────────
        if words & _NEXT_WORDS:
            self._speak("Next slide")
            return "next"

        # ── Previous ──────────────────────────────────────────────────────────
        if words & _PREV_WORDS:
            self._speak("Previous slide")
            return "prev"

        # ── Spotlight ─────────────────────────────────────────────────────────
        if words & _SPOT_WORDS:
            self._speak("Spotlight toggled")
            return "spotlight"

        # ── Zoom ──────────────────────────────────────────────────────────────
        if words & _ZOOM_WORDS:
            self._speak("Zoom toggled")
            return "zoom"

        # ── Quit ──────────────────────────────────────────────────────────────
        if words & _QUIT_WORDS:
            self._speak("Ending presentation")
            return "quit"

        # ── Go-to slide N ─────────────────────────────────────────────────────
        if words & _GOTO_WORDS:
            n = _extract_number(body)
            if n is not None:
                if 1 <= n <= self.total_slides:
                    self._speak(f"Going to slide {n}")
                    return f"goto:{n}"
                else:
                    self._speak(f"Slide {n} is out of range")
                    return None
            self._speak("I didn't catch a slide number")
            return None

        # Wake word heard but no recognised intent
        print(f"[voice] Unrecognised intent after wake word: '{body}'")
        return None

    # ── TTS ───────────────────────────────────────────────────────────────────

    def _speak(self, text: str):
        """Queue a TTS utterance (non-blocking)."""
        print(f"[voice] → {text}")
        if self._tts_available and self._tts_thread and self._tts_thread.is_alive():
            self._tts_queue.put(text)

    def _tts_loop(self):
        """Dedicated TTS thread — drains _tts_queue; never blocks the listener."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.setProperty("volume", 0.9)
        except Exception as e:
            print(f"[voice] TTS init failed in thread: {e}")
            return

        while True:
            item = self._tts_queue.get()
            if item is None:          # poison pill — exit
                break
            try:
                engine.say(item)
                engine.runAndWait()
            except Exception:
                pass
