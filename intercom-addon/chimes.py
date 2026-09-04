import math
import struct

CHIME_MS = 120
FADE_MS = 5


def wav_header(pcm_len: int, *, sample_rate: int, channels: int, sample_width: int) -> bytes:
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + pcm_len,
        b"WAVE",
        b"fmt ",
        16,
        1,                                        # PCM
        channels,
        sample_rate,
        sample_rate * channels * sample_width,    # byte rate
        channels * sample_width,                  # block align
        sample_width * 8,                         # bits per sample
        b"data",
        pcm_len,
    )


class ChimeMixer:
    """Pre-generates pre/post chimes at the configured audio format and
    builds full WAVs by concatenating chime_in + payload + chime_out."""

    def __init__(self, sample_rate: int, sample_width: int, channels: int):
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        self.chime_in = self._generate_chime(800, 1200)
        self.chime_out = self._generate_chime(1200, 800)

    def _generate_chime(self, freq_start: float, freq_end: float) -> bytes:
        """Generate a CHIME_MS sine sweep with linear fade-in/out."""
        if self.sample_width != 2:
            raise ValueError("chimes only support 16-bit PCM in v1")
        n_samples = int(self.sample_rate * CHIME_MS / 1000)
        n_fade = max(1, int(self.sample_rate * FADE_MS / 1000))
        amplitude = 16000  # ~half-scale for int16
        samples = bytearray()
        for i in range(n_samples):
            t = i / self.sample_rate
            freq = freq_start + (freq_end - freq_start) * (i / n_samples)
            value = math.sin(2 * math.pi * freq * t)
            if i < n_fade:
                env = i / n_fade
            elif i > n_samples - n_fade:
                env = (n_samples - i) / n_fade
            else:
                env = 1.0
            v_int = int(value * env * amplitude)
            for _ in range(self.channels):
                samples.extend(struct.pack("<h", v_int))
        return bytes(samples)

    def build_wav(self, pcm: bytes) -> bytes:
        """Return a full WAV byte string: header + chime_in + pcm + chime_out."""
        body = self.chime_in + pcm + self.chime_out
        return wav_header(
            len(body),
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
        ) + body

    def build_plain_wav(self, pcm: bytes) -> bytes:
        """Return the payload as a WAV with no chimes around it — what you want
        when judging the microphone rather than playing a broadcast."""
        return wav_header(
            len(pcm),
            sample_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.sample_width,
        ) + pcm

    def pcm_duration_seconds(self, pcm: bytes) -> float:
        return len(pcm) / (self.sample_rate * self.sample_width * self.channels)

    def total_duration_seconds(self, pcm: bytes) -> float:
        return self.pcm_duration_seconds(self.chime_in + pcm + self.chime_out)
