"""E01: estimadores de f0 em senoides sintéticas e em silêncio.

Varre as notas cromáticas de A4 a F6 (faixa nominal de uma ocarina Alto C de
12 furos) e compara FFT, FFT com interpolação, autocorrelação e YIN para
várias janelas, taxas de amostragem e níveis de ruído.

Uso: python experimentos/e01_sinteticos.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ocarina_beat.estimador import METODOS  # noqa: E402
from ocarina_beat.notas import cents, midi_para_freq  # noqa: E402

FMIN, FMAX = 400.0, 1500.0
NOTAS = range(69, 90)  # A4 .. F6
SNRS_DB = [None, 20, 10]


def gerar(f, fs, n, snr_db, rng):
    t = np.arange(n) / fs
    x = 0.5 * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    if snr_db is not None:
        pot_ruido = np.mean(x**2) / 10 ** (snr_db / 10)
        x = x + rng.normal(0, np.sqrt(pot_ruido), n)
    return x


def main():
    rng = np.random.default_rng(0)
    print("| fs (Hz) | N | SNR | método | erro médio (cents) | erro máx (cents) | sem estimativa | erro de oitava |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for fs in (48000, 44100):
        for n in (1024, 2048, 4096):
            for snr in SNRS_DB:
                for nome, metodo in METODOS.items():
                    erros, vazios, oitavas = [], 0, 0
                    for k in NOTAS:
                        # 3 desvios por nota: exata, +20 e -20 cents
                        for desvio in (0, 20, -20):
                            f = midi_para_freq(k) * 2 ** (desvio / 1200)
                            f0, _ = metodo(gerar(f, fs, n, snr, rng), fs, FMIN, FMAX)
                            if f0 is None:
                                vazios += 1
                                continue
                            e = cents(f0, f)
                            if abs(abs(e) - 1200) < 100 or abs(abs(e) - 2400) < 100:
                                oitavas += 1
                            else:
                                erros.append(abs(e))
                    medio = f"{np.mean(erros):.2f}" if erros else "-"
                    maximo = f"{np.max(erros):.2f}" if erros else "-"
                    snr_txt = "sem ruído" if snr is None else f"{snr} dB"
                    print(f"| {fs} | {n} | {snr_txt} | {nome} | {medio} | {maximo} | {vazios} | {oitavas} |")
    # silêncio e ruído sem tom: não podem virar nota
    print()
    print("Silêncio e ruído branco (esperado: nenhuma estimativa):")
    for nome, metodo in METODOS.items():
        falsos = 0
        total = 200
        for amp in (0.0, 0.0005, 0.05):
            for _ in range(total // 3):
                x = rng.normal(0, amp, 2048) if amp else np.zeros(2048)
                if metodo(x, 48000, FMIN, FMAX)[0] is not None:
                    falsos += 1
        print(f"- {nome}: {falsos} falsas estimativas em {3 * (total // 3)} janelas")


if __name__ == "__main__":
    main()
