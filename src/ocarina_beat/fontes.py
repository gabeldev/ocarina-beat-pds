"""Fontes de áudio: cada uma devolve (fs, iterador de blocos mono)."""

import time

import numpy as np

from . import audio

BLOCO = 512


def _em_blocos(x):
    return (x[i : i + BLOCO] for i in range(0, len(x), BLOCO))


def simulada(cancao, bpm=100, ruido=0.0, silencio_fim=2.0):
    x = np.concatenate([np.zeros(audio.FS // 2), audio.cancao(cancao, bpm), np.zeros(int(audio.FS * silencio_fim))])
    x = x + ruido * np.random.default_rng(0).standard_normal(len(x))
    return audio.FS, _em_blocos(x)


def arquivo(caminho):
    from scipy.io import wavfile

    fs, x = wavfile.read(caminho)
    if x.dtype.kind == "i":
        x = x.astype(float) / np.iinfo(x.dtype).max
    x = x.astype(float)
    return fs, _em_blocos(x[:, 0] if x.ndim > 1 else x)


def microfone(dispositivo=None, segundos=None):
    from .captura import abrir_entrada

    stream, info = abrir_entrada(dispositivo, 48000, canais=1, bloco=BLOCO)

    def gerar():
        fim = None if segundos is None else time.time() + segundos
        with stream:
            while fim is None or time.time() < fim:
                bloco, _ = stream.read(BLOCO)
                yield bloco[:, 0]

    return info.fs_efetiva, gerar(), info


def em_tempo_real(fs, blocos):
    """Entrega os blocos no ritmo do relógio (para simular um microfone)."""
    inicio, n = time.time(), 0
    for b in blocos:
        n += len(b)
        atraso = inicio + n / fs - time.time()
        if atraso > 0:
            time.sleep(atraso)
        yield b
