#!/usr/bin/env python3
"""Generate the light instrumental music bed (10 s, 48 kHz stereo WAV) for the intro/outro windows.

Original, procedurally synthesised (no samples, no lyrics): soft sine/triangle pads on a
Cmaj7 - Am7 - Fmaj7 - G6 progression (2.5 s per chord) plus a gentle bell arpeggio.
Deterministic: the same output on every run.
Usage: python3 make_music.py <out.wav> [variant]   variant: intro | outro (outro arpeggio descends)
"""
import math, struct, sys, wave

SR, DUR = 48000, 10.0
N = int(SR * DUR)
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)
CHORDS = [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 52, 59]]  # C E G B.. voicings
ARP = [[72, 76, 79, 83], [69, 72, 76, 79], [65, 69, 72, 76], [67, 71, 74, 76]]

def main(out, variant):
    L = [0.0] * N; R = [0.0] * N
    seg = DUR / len(CHORDS)
    for ci, chord in enumerate(CHORDS):
        t0 = ci * seg
        for k, m in enumerate(chord):
            f = hz(m); pan = 0.35 + 0.1 * k
            s0, s1 = int(t0 * SR), min(N, int((t0 + seg + 0.6) * SR))
            for i in range(s0, s1):
                t = i / SR - t0
                env = min(1.0, t / 0.8) * (1.0 if t < seg else max(0.0, 1 - (t - seg) / 0.6))
                v = env * 0.05 * (math.sin(2 * math.pi * f * t) + 0.18 * math.sin(4 * math.pi * f * t + 0.3))
                v *= 1 + 0.08 * math.sin(2 * math.pi * 0.25 * (i / SR) + k)
                L[i] += v * (1 - pan); R[i] += v * pan
        notes = ARP[ci] if variant == "intro" else list(reversed(ARP[ci]))
        for j, m in enumerate(notes):
            f = hz(m); ts = t0 + j * seg / 4; pan = 0.3 + 0.13 * j
            s0, s1 = int(ts * SR), min(N, int((ts + 1.6) * SR))
            for i in range(s0, s1):
                t = i / SR - ts
                env = min(1.0, t / 0.01) * math.exp(-t * 2.8)
                v = env * 0.035 * (math.sin(2 * math.pi * f * t) + 0.25 * math.sin(2 * math.pi * 2.01 * f * t))
                L[i] += v * (1 - pan); R[i] += v * pan
    peak = max(max(abs(x) for x in L), max(abs(x) for x in R))
    g = 0.5 / peak
    with wave.open(out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<hh", int(L[i] * g * 32767), int(R[i] * g * 32767)) for i in range(N)))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "intro")
