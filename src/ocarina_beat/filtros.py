"""Pré-filtragem do áudio antes do estimador de f0: passa-faixa IIR ou FIR.

A flauta doce do repertório soa entre ~520 Hz (Dó5) e ~1.800 Hz (Lá6), com harmônicos acima.
- passa-altas em F_BAIXA (400 Hz): corta ventilador, vibração, rede elétrica e a maior parte da voz grave;
- passa-baixas em F_ALTA (5 kHz): corta chiado, mantendo o 2º harmônico das notas agudas (ajuda o YIN).

Duas implementações, para comparar (experimentos/e_filtro.py):
- IIR Butterworth em seções de 2ª ordem (SOS): barato, pouco atraso, fase não linear;
- FIR por janela (Hamming): fase linear e sempre estável, mais caro e com atraso de (N-1)/2 amostras.
Os filtros guardam estado entre blocos (filtragem em fluxo, sem estalos nas emendas).
"""

from dataclasses import dataclass

import numpy as np
from scipy import signal

F_BAIXA = 400.0
F_ALTA = 5000.0
ORDEM_IIR = 4  # ordem de cada lado (passa-faixa resultante tem ordem 2*ORDEM_IIR)
TAPS_FIR = 255  # ímpar: atraso inteiro de (N-1)/2 amostras


@dataclass
class Projeto:
    tipo: str  # "iir" ou "fir"
    fs: float
    sos: np.ndarray | None = None  # IIR
    taps: np.ndarray | None = None  # FIR

    def resposta(self, freqs):
        """Ganho em dB nas frequências pedidas (Hz)."""
        w = 2 * np.pi * np.asarray(freqs, dtype=float) / self.fs
        if self.tipo == "iir":
            _, h = signal.sosfreqz(self.sos, worN=w)
        else:
            _, h = signal.freqz(self.taps, worN=w)
        return 20 * np.log10(np.maximum(np.abs(h), 1e-12))

    def polos(self):
        """Polos do filtro (vazio para FIR, que só tem zeros e é sempre estável)."""
        if self.tipo == "fir":
            return np.array([])
        return np.concatenate([np.roots(s[3:]) for s in self.sos])

    def estavel(self):
        """Causal e estável: todos os polos dentro do círculo unitário."""
        return bool(np.all(np.abs(self.polos()) < 1.0))

    def atraso_amostras(self):
        """Atraso de grupo aproximado na faixa da flauta (amostras)."""
        if self.tipo == "fir":
            return (len(self.taps) - 1) / 2
        w = 2 * np.pi * np.array([700.0, 1000.0, 1500.0]) / self.fs
        b, a = signal.sos2tf(self.sos)
        _, gd = signal.group_delay((b, a), w=w)
        return float(np.mean(gd))


def projetar(tipo, fs, f_baixa=F_BAIXA, f_alta=F_ALTA, ordem=ORDEM_IIR, taps=TAPS_FIR):
    f_alta = min(f_alta, 0.45 * fs)  # respeita Nyquist com folga
    if tipo == "iir":
        sos = signal.butter(ordem, [f_baixa, f_alta], btype="bandpass", fs=fs, output="sos")
        return Projeto("iir", fs, sos=sos)
    if tipo == "fir":
        h = signal.firwin(taps, [f_baixa, f_alta], pass_zero=False, window="hamming", fs=fs)
        return Projeto("fir", fs, taps=h)
    raise ValueError(f"tipo de filtro desconhecido: {tipo!r}")


class FiltroFluxo:
    """Aplica o filtro bloco a bloco, mantendo o estado interno entre chamadas."""

    def __init__(self, projeto):
        self.p = projeto
        if projeto.tipo == "iir":
            self._z = np.zeros((projeto.sos.shape[0], 2))
        else:
            self._z = np.zeros(len(projeto.taps) - 1)

    def __call__(self, x):
        x = np.asarray(x, dtype=float)
        if self.p.tipo == "iir":
            y, self._z = signal.sosfilt(self.p.sos, x, zi=self._z)
        else:
            y, self._z = signal.lfilter(self.p.taps, [1.0], x, zi=self._z)
        return y
