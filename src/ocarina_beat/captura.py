"""Captura de áudio do microfone com sounddevice (PortAudio)."""

from dataclasses import dataclass

import numpy as np
import sounddevice as sd

FS_PREFERIDA = 48000


@dataclass
class InfoEntrada:
    """Dados da entrada de áudio efetivamente aberta (RF02)."""

    dispositivo: int
    nome: str
    api: str
    fs_pedida: int
    fs_efetiva: float
    canais: int
    latencia_s: float


def listar_entradas():
    """Dispositivos com pelo menos uma entrada: [(indice, nome, api, canais, fs_padrao)]."""
    apis = sd.query_hostapis()
    return [
        (i, d["name"], apis[d["hostapi"]]["name"], d["max_input_channels"], d["default_samplerate"])
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] > 0
    ]


def escolher_fs(dispositivo, canais, fs_pedida=FS_PREFERIDA):
    """Usa a taxa pedida se o dispositivo aceitar; senão, a padrão dele."""
    try:
        sd.check_input_settings(device=dispositivo, channels=canais, samplerate=fs_pedida)
        return fs_pedida
    except sd.PortAudioError:
        return int(sd.query_devices(dispositivo, "input")["default_samplerate"])


def abrir_entrada(dispositivo=None, fs_pedida=FS_PREFERIDA, canais=1, bloco=1024):
    """Abre o stream de entrada e devolve (stream, InfoEntrada). Use como contexto."""
    idx = sd.default.device[0] if dispositivo is None else dispositivo
    dev = sd.query_devices(idx, "input")
    canais = min(canais, dev["max_input_channels"])
    fs = escolher_fs(idx, canais, fs_pedida)
    stream = sd.InputStream(device=idx, channels=canais, samplerate=fs, blocksize=bloco, dtype="float32")
    info = InfoEntrada(
        dispositivo=idx,
        nome=dev["name"],
        api=sd.query_hostapis(dev["hostapi"])["name"],
        fs_pedida=fs_pedida,
        fs_efetiva=stream.samplerate,
        canais=canais,
        latencia_s=stream.latency,
    )
    return stream, info


def gravar(segundos, dispositivo=None, fs_pedida=FS_PREFERIDA, canais=1):
    """Grava um trecho. Devolve (amostras float32 de forma (n, canais), InfoEntrada)."""
    stream, info = abrir_entrada(dispositivo, fs_pedida, canais)
    n = int(segundos * info.fs_efetiva)
    with stream:
        x, estouro = stream.read(n)
    if estouro:
        print("aviso: houve perda de amostras (overflow) na captura")
    return x, info
