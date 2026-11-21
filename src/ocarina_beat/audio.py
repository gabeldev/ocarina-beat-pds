"""Síntese e reprodução: referência das canções, reações e avisos.

O timbre é uma flauta simples: fundamental + 2º harmônico fraco, leve vibrato
tardio e ataque/release curtos. Serve de guia sonoro e de sinal de teste.
"""

import numpy as np

from .notas import midi_para_freq

FS = 48000


def _env(n, fs, ataque=0.02, release=0.05):
    a, r = max(int(ataque * fs), 1), max(int(release * fs), 1)
    env = np.ones(n)
    k = min(a, n)
    env[:k] = np.linspace(0, 1, k)
    k = min(r, n)
    env[n - k :] *= np.linspace(1, 0, k)
    return env


def nota(midi, dur, fs=FS, amp=0.3, vibrato=True):
    n = int(dur * fs)
    t = np.arange(n) / fs
    f = midi_para_freq(midi)
    # vibrato leve (5 Hz, ±3 cents) só depois de 0,15 s
    desvio = 0.0017 * np.sin(2 * np.pi * 5 * t) * np.clip((t - 0.15) / 0.2, 0, 1) if vibrato else np.zeros(n)
    fase = 2 * np.pi * np.cumsum(f * (1 + desvio)) / fs
    return amp * _env(n, fs) * (np.sin(fase) + 0.12 * np.sin(2 * fase))


def cancao(c, bpm=100, fs=FS, articulacao=0.06, n_notas=None):
    """Toca a canção do JSON: cada nota dura `beats` e termina com uma pausa curta
    (assim as repetidas se separam). `n_notas` limita ao começo."""
    seg = 60.0 / bpm
    partes = []
    for a in c["notes"][:n_notas]:
        d = a["beats"] * seg
        partes.append(nota(a["midi"], max(d - articulacao, 0.05), fs, vibrato=d > 0.4))
        partes.append(np.zeros(int(min(articulacao, d * 0.5) * fs)))
    return np.concatenate(partes)


def reacao(c, fs=FS):
    """Pequeno arpejo ascendente nas notas do começo da canção, com acorde final."""
    base = [a["midi"] for a in c["notes"][:3]]
    notas = [nota(m, 0.12, fs, vibrato=False) for m in base]
    topo = max(base) + 12
    fim = sum(nota(m, 0.5, fs, amp=0.15, vibrato=False) for m in (topo, topo + 4, topo + 7))
    return np.concatenate(notas + [fim])


def erro(fs=FS):
    return np.concatenate([nota(64, 0.12, fs, vibrato=False), nota(58, 0.25, fs, vibrato=False)])


def acerto_parcial(fs=FS):
    return nota(84, 0.06, fs, amp=0.15, vibrato=False)


def tocar(x, fs=FS, bloquear=True):
    import sounddevice as sd

    sd.play(np.asarray(x, dtype=np.float32), fs)
    if bloquear:
        sd.wait()
