"""Gravador de sessões rotuladas: WAV + metadados JSON em dados/brutos/AAAA-MM-DD/.

    python -m ocarina_beat.gravador --tipo cancao --alvo epona_song --executante gabriel
    python -m ocarina_beat.gravador --tipo nota --alvo A5 --executante gabriel --segundos 8
    python -m ocarina_beat.gravador --tipo silencio --executante gabriel --condicao "ventilador ligado"
    python -m ocarina_beat.gravador --listar

Tipos: nota (alvo = nota, ex. A5), cancao (alvo = id), erro (alvo = id; descreva o erro em --obs),
silencio, fala, ruido, livre. Durante a gravação o ganho do microfone fica fixo (o valor é registrado),
para as sessões serem comparáveis. As gravações ficam fora do Git (dados/brutos/ está no .gitignore).
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .captura import abrir_entrada
from .ganho import ControleGanho
from .instrumento import INSTRUMENTOS, PADRAO
from .jogo import Jogo
from .motor import Processador
from .notas import nome_nota
from .reconhecedor import carregar_repertorio

RAIZ = Path(__file__).resolve().parents[2]
PASTA = RAIZ / "dados" / "brutos"
TIPOS = ["nota", "cancao", "erro", "silencio", "fala", "ruido", "livre"]
BLOCO = 1024


def dbfs(v):
    return 20 * np.log10(max(float(v), 1e-9))


def _versao():
    try:
        return subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=2).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def gravar_sessao(args):
    stream, info = abrir_entrada(args.dispositivo, 48000, canais=1, bloco=BLOCO)
    volume = ControleGanho().atual  # só lê; o ganho não muda durante a gravação
    print(f"Entrada: {info.nome} @ {info.fs_efetiva:.0f} Hz | volume do microfone: "
          f"{'?' if volume is None else format(volume, '.0%')}")
    if not args.sem_contagem:
        for i in (3, 2, 1):
            print(f"  começa em {i}...", end="\r", flush=True)
            time.sleep(1)
    print(f"GRAVANDO {args.segundos:.0f} s — {args.tipo}{' ' + args.alvo if args.alvo else ''}      ")
    partes, estouros = [], 0
    n_total = int(args.segundos * info.fs_efetiva)
    lidos = 0
    with stream:
        stream.read(int(0.3 * info.fs_efetiva))  # descarta o estalo de abertura do microfone
        while lidos < n_total:
            bloco, estouro = stream.read(min(BLOCO, n_total - lidos))
            estouros += bool(estouro)
            x = bloco[:, 0].copy()
            partes.append(x)
            lidos += len(x)
            nivel = dbfs(np.sqrt(np.mean(x**2)))
            barra = "#" * int(max(0, (nivel + 70) / 2))
            print(f"  {lidos / info.fs_efetiva:5.1f} s  {nivel:6.1f} dBFS  {barra:<35}", end="\r", flush=True)
    print()
    x = np.concatenate(partes).astype(np.float32)
    pico = float(np.abs(x).max()) if len(x) else 0.0

    agora = datetime.now()
    pasta = PASTA / agora.strftime("%Y-%m-%d")
    pasta.mkdir(parents=True, exist_ok=True)
    nome = "_".join(p for p in [agora.strftime("%H%M%S"), args.tipo, args.alvo, args.executante] if p)
    wav, meta = pasta / f"{nome}.wav", pasta / f"{nome}.json"
    wavfile.write(wav, int(round(info.fs_efetiva)), x)
    dados = {
        "id": nome, "criado_em": agora.isoformat(timespec="seconds"),
        "tipo": args.tipo, "alvo": args.alvo, "executante": args.executante,
        "condicao": args.condicao, "obs": args.obs, "instrumento": args.instrumento,
        "fs_hz": info.fs_efetiva, "duracao_s": round(len(x) / info.fs_efetiva, 3),
        "dispositivo": info.nome, "api": info.api, "latencia_s": round(info.latencia_s, 4),
        "volume_microfone": volume, "pico_dbfs": round(dbfs(pico), 1),
        "rms_dbfs": round(dbfs(np.sqrt(np.mean(x.astype(float) ** 2))), 1), "saturou": pico >= 0.99,
        "overflows": estouros, "versao_codigo": _versao(),
    }
    meta.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"Salvo: {wav.relative_to(RAIZ)} (+ .json)")
    if dados["saturou"]:
        print("AVISO: saturou. Afaste a flauta ou baixe o volume do microfone e grave de novo.")
    resumo(x.astype(float), info.fs_efetiva, args.instrumento)


def resumo(x, fs, instrumento):
    """Conferência rápida: notas detectadas e canção reconhecida (com o filtro padrão)."""
    p = Processador(fs, instrumento)
    rep = carregar_repertorio(RAIZ / "repertorio")
    j = Jogo(rep, "livre") if rep else None
    eventos = []
    for i in range(0, len(x), 512):
        p.alimentar(x[i : i + 512])
        if j:
            eventos += j.atualizar(p.notas, p.tempo)
    notas = p.finalizar()
    if j:
        eventos += j.atualizar(p.notas, p.tempo)
    print(f"Notas detectadas ({len(notas)}): " + " ".join(nome_nota(n.midi) for n in notas[:40]))
    rec = [e.dados["nome"] for e in eventos if e.tipo == "reconhecida"]
    if rec:
        print("Canção reconhecida: " + ", ".join(rec))


def listar():
    metas = sorted(PASTA.glob("*/*.json"))
    if not metas:
        print("Nenhuma sessão gravada ainda em dados/brutos/.")
        return
    for m in metas:
        d = json.loads(m.read_text())
        print(f"{d['criado_em']}  {d['tipo']:<9} {d.get('alvo') or '-':<15} {d['executante']:<10} "
              f"{d['duracao_s']:5.1f} s  pico {d['pico_dbfs']:6.1f} dBFS  {d.get('condicao') or ''}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--tipo", choices=TIPOS)
    ap.add_argument("--alvo", default="", help="nota (ex. A5) ou id da canção")
    ap.add_argument("--executante", default="")
    ap.add_argument("--condicao", default="normal", help="ex.: '30 cm, quarto silencioso', 'ventilador ligado'")
    ap.add_argument("--obs", default="")
    ap.add_argument("--segundos", type=float, default=20.0)
    ap.add_argument("--instrumento", choices=sorted(INSTRUMENTOS), default=PADRAO)
    ap.add_argument("--dispositivo", type=int)
    ap.add_argument("--sem-contagem", action="store_true")
    args = ap.parse_args(argv)
    if args.listar:
        return listar()
    if not args.tipo or not args.executante:
        sys.exit("informe --tipo e --executante (ou use --listar)")
    if args.tipo in ("nota", "cancao", "erro") and not args.alvo:
        sys.exit(f"--tipo {args.tipo} precisa de --alvo")
    gravar_sessao(args)


if __name__ == "__main__":
    main()
