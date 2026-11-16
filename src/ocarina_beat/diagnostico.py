"""Tela de diagnóstico no terminal: nível, frequência e nota em tempo real.

Uso:
    python -m ocarina_beat.diagnostico --listar
    python -m ocarina_beat.diagnostico --segundos 10 [--dispositivo N] [--metodo yin]
"""

import argparse
import time

import numpy as np

from .captura import abrir_entrada, listar_entradas
from .estimador import METODOS, rms
from .notas import nome_nota, nota_mais_proxima

FMIN, FMAX = 400.0, 1500.0  # faixa nominal de uma ocarina Alto C; ajustar após medir
JANELA = 2048


def dbfs(valor):
    return 20 * np.log10(max(valor, 1e-9))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listar", action="store_true", help="lista as entradas e sai")
    ap.add_argument("--dispositivo", type=int, default=None)
    ap.add_argument("--fs", type=int, default=48000, help="taxa pedida (Hz)")
    ap.add_argument("--segundos", type=float, default=10.0)
    ap.add_argument("--metodo", choices=sorted(METODOS), default="yin")
    args = ap.parse_args()

    if args.listar:
        for i, nome, api, canais, fs in listar_entradas():
            print(f"{i:3d}  {nome}  [{api}]  {canais} canais  padrão {fs:.0f} Hz")
        return

    stream, info = abrir_entrada(args.dispositivo, args.fs, canais=1, bloco=1024)
    print(f"Dispositivo: {info.dispositivo} - {info.nome} [{info.api}]")
    print(f"Taxa pedida: {info.fs_pedida} Hz | efetiva: {info.fs_efetiva:.0f} Hz | latência: {info.latencia_s * 1000:.1f} ms")
    print(f"Método: {args.metodo} | janela: {JANELA} amostras ({1000 * JANELA / info.fs_efetiva:.1f} ms) | faixa: {FMIN:.0f}-{FMAX:.0f} Hz\n")
    metodo = METODOS[args.metodo]

    buf = np.zeros(JANELA, dtype=np.float32)
    pico, estouros, blocos = 0.0, 0, 0
    fim = time.time() + args.segundos
    with stream:
        while time.time() < fim:
            bloco, estouro = stream.read(1024)
            estouros += bool(estouro)
            blocos += 1
            x = bloco[:, 0]
            buf = np.concatenate([buf[len(x):], x])
            pico = max(pico, float(np.abs(x).max()))
            nivel = rms(buf)
            f0, conf = metodo(buf, info.fs_efetiva, FMIN, FMAX)
            barra = "#" * int(max(0, (dbfs(nivel) + 80) / 2))
            if f0 is None:
                print(f"{dbfs(nivel):6.1f} dBFS  {'-':>9}  {'-':>4}  {'':>8}  {barra}")
            else:
                k, c = nota_mais_proxima(f0)
                print(f"{dbfs(nivel):6.1f} dBFS  {f0:7.1f} Hz  {nome_nota(k):>4}  {c:+6.1f} ct  {barra}")
    print(f"\nPico: {dbfs(pico):.1f} dBFS{' (SATUROU)' if pico >= 0.99 else ''} | blocos: {blocos} | overflows: {estouros}")


if __name__ == "__main__":
    main()
