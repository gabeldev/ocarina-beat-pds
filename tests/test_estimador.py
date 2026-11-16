import numpy as np
import pytest

from ocarina_beat.estimador import METODOS
from ocarina_beat.notas import cents, midi_para_freq

FS, N = 48000, 2048
FMIN, FMAX = 400.0, 1500.0
NOTAS = range(69, 90)  # A4 .. F6


def senoide(f, n=N, fs=FS, fase=0.3, amp=0.5):
    return amp * np.sin(2 * np.pi * f * np.arange(n) / fs + fase)


@pytest.mark.parametrize("metodo,tolerancia", [("fft_interp", 3.0), ("autocorr", 5.0), ("yin", 3.0)])
def test_senoide_limpa_dentro_da_tolerancia(metodo, tolerancia):
    for k in NOTAS:
        f = midi_para_freq(k)
        f0, _ = METODOS[metodo](senoide(f), FS, FMIN, FMAX)
        assert f0 is not None, f"{metodo} sem estimativa em {f:.1f} Hz"
        assert abs(cents(f0, f)) < tolerancia, f"{metodo}: erro em {f:.1f} Hz"


def test_fft_sem_interpolacao_e_pior_nas_notas_graves():
    f = midi_para_freq(69) * 2 ** (20 / 1200)
    sem, _ = METODOS["fft"](senoide(f), FS, FMIN, FMAX)
    com, _ = METODOS["fft_interp"](senoide(f), FS, FMIN, FMAX)
    assert abs(cents(sem, f)) > abs(cents(com, f))


@pytest.mark.parametrize("metodo", sorted(METODOS))
def test_silencio_nao_gera_nota(metodo):
    assert METODOS[metodo](np.zeros(N), FS, FMIN, FMAX)[0] is None


@pytest.mark.parametrize("metodo", sorted(METODOS))
def test_ruido_branco_nao_gera_nota(metodo):
    rng = np.random.default_rng(1)
    falsos = sum(
        METODOS[metodo](rng.normal(0, 0.05, N), FS, FMIN, FMAX)[0] is not None for _ in range(100)
    )
    assert falsos <= 2


@pytest.mark.parametrize("metodo", sorted(METODOS))
def test_sem_erro_de_oitava_em_senoide_limpa(metodo):
    for k in NOTAS:
        f = midi_para_freq(k)
        f0, _ = METODOS[metodo](senoide(f), FS, FMIN, FMAX)
        assert abs(cents(f0, f)) < 100
