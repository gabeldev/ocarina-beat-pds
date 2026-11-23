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


def sino(midi, dur, fs=FS, amp=0.22):
    """Nota com timbre de sino/celesta: ataque rápido e decaimento exponencial."""
    n = int(dur * fs)
    t = np.arange(n) / fs
    f = midi_para_freq(midi)
    env = np.exp(-t * 4.0) * np.minimum(1, t / 0.004)
    onda = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 6) + 0.12 * np.sin(2 * np.pi * 3.01 * f * t) * np.exp(-t * 9)
    return amp * env * onda


def sucesso(fs=FS):
    """Fanfarra curta de acerto: arpejo de Dó maior subindo e acorde final soando."""
    passo = 0.085
    notas = [72, 76, 79, 84]
    total = int((passo * len(notas) + 1.4) * fs)
    x = np.zeros(total)
    for i, m in enumerate(notas):
        ini = int(i * passo * fs)
        s = sino(m, 0.6, fs)
        x[ini : ini + len(s)] += s[: total - ini]
    ini = int(len(notas) * passo * fs)
    for m in (84, 88, 91, 96):  # acorde final (Dó maior aberto)
        s = sino(m, 1.4, fs, amp=0.13)
        x[ini : ini + len(s)] += s[: total - ini]
    return x / max(1.0, np.abs(x).max() / 0.6)


def erro(fs=FS):
    return np.concatenate([nota(64, 0.12, fs, vibrato=False), nota(58, 0.25, fs, vibrato=False)])


def acerto_parcial(fs=FS):
    return nota(84, 0.06, fs, amp=0.15, vibrato=False)


def tocar(x, fs=FS, bloquear=True):
    import sounddevice as sd

    sd.play(np.asarray(x, dtype=np.float32), fs)
    if bloquear:
        sd.wait()
