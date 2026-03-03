"""
Voice Controller for Gesture Presentation Engine.

Cross-platform replacement for the win32com/PowerPoint approach in voice.py.
Listens for a wake word then routes commands into a shared queue that the
engine drains each frame.

Wake word : "computer"
Commands  : next / forward
            previous / back
            go to slide N / jump to slide N
            spotlight
            exit / quit / end
"""

import re
import queue
import threading

import speech_recognition as sr

WAKE_WORD = "computer"

try:
    import pyttsx3
    _TTS_AVAILABLE = True
except Exception:
    _TTS_AVAILABLE = False


class VoiceController:
    """
    Runs speech recognition in a daemon thread.
    Puts command strings into `cmd_queue` for the engine to consume.

    Command tokens placed on the queue
    -----------------------------------
    "next"       – advance one slide
    "prev"       – go back one slide
    "goto:N"     – jump to slide number N (1-based)
    "spotlight"  – toggle spotlight
    "quit"       – end the presentation
    """

    def __init__(self, cmd_queue: queue.Queue, total_slides: int):
        self.q            = cmd_queue
        self.total_slides = total_slides
        self.recognizer   = sr.Recognizer()
        self._stop        = threading.Event()
        self._thread      = None

        # TTS (optional — gracefully disabled if unavailable)
        self._tts = None
        if _TTS_AVAILABLE:
            try:
                self._tts = pyttsx3.init()
                self._tts.setProperty("rate", 150)
            except Exception:
                self._tts = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Start the background listening thread."""
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"[voice] Listening for wake word: '{WAKE_WORD}'")

    def stop(self):
        """Signal the listening thread to exit."""
        self._stop.set()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _speak(self, text: str):
        print(f"[voice] {text}")
        if self._tts:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except Exception:
                pass

    def _parse(self, text: str):
        """
        Return a command token if the wake word is present, else None.
        Mirrors voice.py's parse_command / execute_command logic but
        adapted for our engine's queue protocol.
        """
        text = text.lower().strip()
        if not text.startswith(WAKE_WORD):
            return None

        body = text[len(WAKE_WORD):].strip()

        if "next" in body or "forward" in body:
            self._speak("Next slide")
            return "next"

        if "previous" in body or "back" in body:
            self._speak("Previous slide")
            return "prev"

        if "spotlight" in body:
            self._speak("Spotlight toggled")
            return "spotlight"

        if "exit" in body or "quit" in body or "end" in body:
            self._speak("Ending presentation")
            return "quit"

        if "go to slide" in body or "jump to slide" in body:
            m = re.search(r"\d+", body)
            if m:
                n = int(m.group())
                if 1 <= n <= self.total_slides:
                    self._speak(f"Going to slide {n}")
                    return f"goto:{n}"
                else:
                    self._speak(f"Slide {n} is out of range")
                    return None
            self._speak("I didn't catch a slide number")
            return None

        # Wake word heard but command not recognised — just log
        print(f"[voice] Unknown command: '{body}'")
        return None

    def _listen_loop(self):
        try:
            with sr.Microphone() as source:
                print("[voice] Adjusting for ambient noise…")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("[voice] Ready.")

                while not self._stop.is_set():
                    try:
                        audio = self.recognizer.listen(
                            source, timeout=3, phrase_time_limit=5
                        )
                        text = self.recognizer.recognize_google(audio)
                        print(f"[voice] Heard: '{text}'")
                        cmd = self._parse(text)
                        if cmd:
                            self.q.put(cmd)

                    except sr.WaitTimeoutError:
                        pass  # nothing heard in 3 s — loop and check _stop
                    except sr.UnknownValueError:
                        pass  # unintelligible audio
                    except sr.RequestError as e:
                        print(f"[voice] API error: {e}")
                    except Exception as e:
                        print(f"[voice] Error: {e}")

        except Exception as e:
            print(f"[voice] Microphone error: {e}")
