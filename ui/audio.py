"""Audio engine for Kriegsspiel.

Produces synthesised sound effects via pygame.mixer when available.
Falls back silently to no-ops if the mixer module is missing or the
audio device is unavailable (headless, CI, or sandboxed environments).

Usage::

    from ui.audio import AudioEngine
    audio = AudioEngine()
    audio.play("cannon_fire")
    audio.play("musket_volley")
    audio.set_volume(0.6)
    audio.toggle_mute()
"""

from __future__ import annotations

import math
import struct
import array
import logging

logger = logging.getLogger(__name__)

# Sound identifiers → (frequency_hz, duration_ms, waveform)
_SOUND_SPECS: dict[str, tuple[float, int, str]] = {
    "cannon_fire":     (80.0,  600, "noise_fade"),
    "musket_volley":   (300.0, 350, "noise_fade"),
    "melee_clash":     (220.0, 400, "square"),
    "cavalry_charge":  (180.0, 800, "saw_fade"),
    "unit_move":       (440.0, 120, "sine_blip"),
    "unit_select":     (660.0,  80, "sine_blip"),
    "order_given":     (520.0, 100, "sine_blip"),
    "routing":         (150.0, 500, "saw_fade"),
    "turn_end":        (392.0, 200, "sine_blip"),
    "game_over_win":   (523.0, 800, "chord_major"),
    "game_over_lose":  (220.0, 800, "saw_fade"),
    "objective_taken": (587.0, 300, "chord_major"),
    "weather_change":  (350.0, 250, "sine_blip"),
}

_SAMPLE_RATE = 44100
_CHANNELS = 1


class AudioEngine:
    """Manages sound effect playback with graceful fallback."""

    def __init__(self, volume: float = 0.5) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._muted = False
        self._available = False
        self._sounds: dict[str, object] = {}
        self._init_mixer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play(self, sound_id: str) -> None:
        """Play a named sound effect (no-op if audio unavailable or muted)."""
        if not self._available or self._muted:
            return
        sound = self._sounds.get(sound_id)
        if sound is not None:
            try:
                sound.set_volume(self._volume)
                sound.play()
            except Exception:
                pass

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))

    def toggle_mute(self) -> bool:
        """Toggle mute state; returns new mute state."""
        self._muted = not self._muted
        return self._muted

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def is_available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_mixer(self) -> None:
        try:
            import pygame.mixer as mixer  # type: ignore[import]
            mixer.pre_init(_SAMPLE_RATE, -16, _CHANNELS, 512)
            mixer.init()
            self._available = True
            self._synthesise_sounds(mixer)
        except Exception as exc:
            logger.debug("Audio unavailable: %s", exc)
            self._available = False

    def _synthesise_sounds(self, mixer: object) -> None:
        for sound_id, (freq, duration_ms, waveform) in _SOUND_SPECS.items():
            try:
                buf = _synthesise(freq, duration_ms, waveform)
                snd = mixer.Sound(buffer=buf)
                self._sounds[sound_id] = snd
            except Exception as exc:
                logger.debug("Failed to synthesise %s: %s", sound_id, exc)


# ------------------------------------------------------------------
# Synthesis helpers
# ------------------------------------------------------------------

def _synthesise(freq: float, duration_ms: int, waveform: str) -> bytes:
    """Generate a PCM audio buffer for a simple synthesised sound."""
    n_samples = int(_SAMPLE_RATE * duration_ms / 1000)
    samples: list[int] = []

    for i in range(n_samples):
        t = i / _SAMPLE_RATE
        fade = _fade_envelope(i, n_samples, waveform)

        if waveform == "sine_blip":
            val = math.sin(2 * math.pi * freq * t)
        elif waveform == "square":
            val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif waveform in ("noise_fade", "saw_fade"):
            if "noise" in waveform:
                import random
                val = random.uniform(-1.0, 1.0)
            else:
                val = 2.0 * ((freq * t) % 1.0) - 1.0
        elif waveform == "chord_major":
            # Root + major third + perfect fifth
            val = (
                math.sin(2 * math.pi * freq * t) +
                math.sin(2 * math.pi * freq * 1.25 * t) +
                math.sin(2 * math.pi * freq * 1.5 * t)
            ) / 3.0
        else:
            val = math.sin(2 * math.pi * freq * t)

        sample = int(val * fade * 32767)
        samples.append(max(-32768, min(32767, sample)))

    return array.array("h", samples).tobytes()


def _fade_envelope(i: int, total: int, waveform: str) -> float:
    """Attack-decay fade envelope (0.0 – 1.0)."""
    attack = int(total * 0.05)
    decay = total - attack
    if i < attack:
        return i / max(1, attack)
    fade_progress = (i - attack) / max(1, decay)
    if "blip" in waveform or "major" in waveform:
        return max(0.0, 1.0 - fade_progress)
    # Exponential decay for noise/saw
    return max(0.0, math.exp(-4.0 * fade_progress))
