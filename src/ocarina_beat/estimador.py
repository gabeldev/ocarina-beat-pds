"""Estimadores de frequência fundamental para uma janela de áudio.

Todos recebem um vetor mono `x`, a taxa `fs` e a faixa de busca [fmin, fmax],
e devolvem `(f0, confianca)`. `f0` é None quando não há estimativa válida
(sinal fraco ou sem periodicidade). A confiança depende do método e não é uma
probabilidade calibrada.
"""

import numpy as np

LIMIAR_RMS = 1e-3  # abaixo disso a janela é tratada como silêncio
LIMIAR_CONF_FFT = 8.0  # pico / média do espectro na faixa; abaixo disso, sem tom


def rms(x):
    """RMS sem a componente contínua (offset do microfone não é sinal)."""
    x = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(np.square(x - x.mean()))))


def _pico_parabolico(a, b, c):
    """Deslocamento (em amostras) do extremo da parábola por três pontos."""
    den = a - 2 * b + c
    return 0.0 if den == 0 else 0.5 * (a - c) / den


def f0_fft(x, fs, fmin, fmax, interpolar=True, limiar_rms=LIMIAR_RMS, limiar_conf=LIMIAR_CONF_FFT):
    """Pico da FFT com janela de Hann; interpolação parabólica opcional.

    A confiança é a razão entre o pico e a média do espectro na faixa; ruído
    sem tom fica abaixo de `limiar_conf` e não gera estimativa.
    """
    x = np.asarray(x, dtype=float)
    if rms(x) < limiar_rms:
        return None, 0.0
    x = (x - x.mean()) * np.hanning(len(x))
    mag = np.abs(np.fft.rfft(x))
    df = fs / len(x)
    lo = max(int(np.floor(fmin / df)), 1)
    hi = min(int(np.ceil(fmax / df)), len(mag) - 2)
    if hi <= lo:
        return None, 0.0
    k = lo + int(np.argmax(mag[lo : hi + 1]))
    delta = 0.0
    if interpolar:
        # parábola sobre o log da magnitude (a janela de Hann é ~gaussiana em dB)
        a, b, c = np.log(mag[k - 1 : k + 2] + 1e-12)
        delta = _pico_parabolico(a, b, c)
    conf = float(mag[k] / (mag[lo : hi + 1].mean() + 1e-12))
    if conf < limiar_conf:
        return None, conf
    return (k + delta) * df, conf


def _faixa_atrasos(fs, fmin, fmax, n):
    tau_min = max(int(np.floor(fs / fmax)), 2)
    tau_max = min(int(np.ceil(fs / fmin)), n // 2)
    return tau_min, tau_max


def f0_autocorr(x, fs, fmin, fmax, limiar_pico=0.5, limiar_rms=LIMIAR_RMS):
    """Autocorrelação normalizada; escolhe o primeiro pico alto (evita submúltiplos)."""
    x = np.asarray(x, dtype=float)
    if rms(x) < limiar_rms:
        return None, 0.0
    x = x - x.mean()
    n = len(x)
    # autocorrelação linear via FFT com zero-padding (evita circularidade)
    espectro = np.fft.rfft(x, 2 * n)
    r = np.fft.irfft(np.abs(espectro) ** 2)[:n]
    if r[0] <= 0:
        return None, 0.0
    # normalização por energia da parte sobreposta: compensa o decaimento com o atraso
    r = r / r[0] * n / (n - np.arange(n))
    tau_min, tau_max = _faixa_atrasos(fs, fmin, fmax, n)
    if tau_max - tau_min < 3:
        return None, 0.0
    seg = r[tau_min - 1 : tau_max + 2]
    # picos locais dentro da faixa
    candidatos = [
        i
        for i in range(1, len(seg) - 1)
        if seg[i] >= seg[i - 1] and seg[i] > seg[i + 1]
    ]
    if not candidatos:
        return None, 0.0
    melhor = max(seg[i] for i in candidatos)
    if melhor < limiar_pico:
        return None, float(melhor)
    i = next(i for i in candidatos if seg[i] >= 0.9 * melhor)
    tau = tau_min - 1 + i + _pico_parabolico(seg[i - 1], seg[i], seg[i + 1])
    return fs / tau, float(seg[i])


def f0_yin(x, fs, fmin, fmax, limiar=0.15, limiar_rms=LIMIAR_RMS):
    """YIN (de Cheveigné e Kawahara, 2002): diferença, normalização e limiar."""
    x = np.asarray(x, dtype=float)
    if rms(x) < limiar_rms:
        return None, 0.0
    x = x - x.mean()
    n = len(x)
    tau_min, tau_max = _faixa_atrasos(fs, fmin, fmax, n)
    w = n - tau_max - 1
    if w < 16 or tau_max - tau_min < 3:
        return None, 0.0
    d = np.zeros(tau_max + 2)
    for tau in range(1, tau_max + 2):
        diff = x[:w] - x[tau : tau + w]
        d[tau] = np.dot(diff, diff)
    # diferença média acumulada normalizada
    soma = np.cumsum(d[1:])
    dn = np.ones_like(d)
    dn[1:] = d[1:] * np.arange(1, len(d)) / np.maximum(soma, 1e-12)
    tau = None
    for t in range(tau_min, tau_max + 1):
        if dn[t] < limiar:
            while t + 1 <= tau_max and dn[t + 1] < dn[t]:
                t += 1
            tau = t
            break
    if tau is None:
        return None, float(1 - dn[tau_min : tau_max + 1].min())
    tau_ref = tau + _pico_parabolico(dn[tau - 1], dn[tau], dn[tau + 1])
    return fs / tau_ref, float(1 - dn[tau])


METODOS = {
    "fft": lambda x, fs, a, b: f0_fft(x, fs, a, b, interpolar=False),
    "fft_interp": f0_fft,
    "autocorr": f0_autocorr,
    "yin": f0_yin,
}
