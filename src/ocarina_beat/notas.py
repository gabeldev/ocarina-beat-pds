"""Conversão entre frequência, nota MIDI e desvio em cents."""

import math

A4_HZ = 440.0
A4_MIDI = 69
NOMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def freq_para_midi(f, a4=A4_HZ):
    """Posição MIDI contínua: m = 69 + 12 log2(f / a4)."""
    if f <= 0:
        raise ValueError("a frequência precisa ser positiva")
    return A4_MIDI + 12 * math.log2(f / a4)


def midi_para_freq(k, a4=A4_HZ):
    """Frequência de uma nota MIDI: f = a4 * 2^((k - 69) / 12)."""
    return a4 * 2 ** ((k - A4_MIDI) / 12)


def cents(f, f_ref):
    """Desvio de f em relação a f_ref, em cents."""
    return 1200 * math.log2(f / f_ref)


def nota_mais_proxima(f, a4=A4_HZ):
    """Retorna (nota MIDI inteira, desvio em cents em relação a ela)."""
    k = round(freq_para_midi(f, a4))
    return k, cents(f, midi_para_freq(k, a4))


def nome_nota(k):
    """Nome com oitava, ex.: 69 -> 'A4'."""
    return f"{NOMES[k % 12]}{k // 12 - 1}"
