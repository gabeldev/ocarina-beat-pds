"""Jogo no terminal (backbone sem interface gráfica).

    python -m ocarina_beat.cli canções
    python -m ocarina_beat.cli ouvir epona_song [--bpm 100]
    python -m ocarina_beat.cli livre   [--arquivo x.wav | --simular epona_song | (microfone)]
    python -m ocarina_beat.cli aprender epona_song [mesmas fontes de áudio]

Eventos saem como texto; com --json, uma linha JSON por evento (o que a interface 3D vai ler).
"""

import argparse
import sys
from pathlib import Path

from . import audio, fontes
from .instrumento import INSTRUMENTOS, PADRAO
from .jogo import Jogo
from .motor import Processador
from .reconhecedor import carregar_repertorio

REPERTORIO = Path(__file__).resolve().parents[2] / "repertorio"


def _linha(ev, json_):
    if json_:
        return ev.para_json()
    d = ev.dados
    if ev.tipo == "nota":
        return f"{ev.t:7.2f}s  nota {d['nome']:>3} ({d['cents']:+.0f} ct)"
    if ev.tipo == "reconhecida":
        return f"{ev.t:7.2f}s  *** {d['nome']} reconhecida (erro de ritmo {d['erro_ritmo']:.2f}) ***"
    if ev.tipo == "progresso":
        return f"{ev.t:7.2f}s  ok {d['tocadas']}/{d['total']}"
    if ev.tipo == "divergencia":
        return f"{ev.t:7.2f}s  erro ({d['motivo']}) na nota {d['posicao'] + 1}: esperada {d['esperada']}, tocada {d['tocada']}"
    if ev.tipo == "completa":
        return f"{ev.t:7.2f}s  *** {d['nome']} completa! ***"
    return f"{ev.t:7.2f}s  {ev.tipo} {d}"


def _som_do_evento(ev, rep, fs):
    c = next((c for c in rep if c["id"] == ev.dados.get("id")), None)
    if ev.tipo in ("reconhecida", "completa") and c:
        audio.tocar(audio.reacao(c), audio.FS)
    elif ev.tipo == "divergencia":
        audio.tocar(audio.erro(), audio.FS)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["canções", "ouvir", "livre", "aprender"])
    ap.add_argument("alvo", nargs="?", help="id da canção (ouvir/aprender)")
    ap.add_argument("--repertorio", type=Path, default=REPERTORIO)
    ap.add_argument("--instrumento", choices=sorted(INSTRUMENTOS), default=PADRAO)
    ap.add_argument("--arquivo", type=Path)
    ap.add_argument("--simular", metavar="ID", help="sintetiza a canção e usa como entrada")
    ap.add_argument("--bpm", type=float, default=100)
    ap.add_argument("--ruido", type=float, default=0.0, help="ruído branco somado à simulação")
    ap.add_argument("--dispositivo", type=int)
    ap.add_argument("--segundos", type=float, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--mudo", action="store_true", help="não toca reações")
    args = ap.parse_args(argv)

    rep = carregar_repertorio(args.repertorio)
    if not rep:
        sys.exit(f"repertório vazio em {args.repertorio} (rode experimentos/gerar_repertorio.py)")
    por_id = {c["id"]: c for c in rep}

    if args.comando == "canções":
        for c in rep:
            print(f"{c['id']:16} {c['nome']:18} {len(c['notes'])} notas (reconhece pelas {c['reconhecer_primeiras']} primeiras)")
        return
    for ident in (args.alvo if args.comando in ("ouvir", "aprender") else None, args.simular):
        if ident is not None and ident not in por_id:
            sys.exit(f"canção desconhecida: {ident!r}. Use: {', '.join(por_id)}")
    if args.comando == "ouvir":
        audio.tocar(audio.cancao(por_id[args.alvo], args.bpm))
        return

    # entrada de áudio
    if args.simular:
        fs, blocos = fontes.simulada(por_id[args.simular], args.bpm, args.ruido)
    elif args.arquivo:
        fs, blocos = fontes.arquivo(args.arquivo)
    else:
        if args.comando == "aprender" and not args.mudo:
            print("Referência:", file=sys.stderr)
            audio.tocar(audio.cancao(por_id[args.alvo], args.bpm))
        fs, blocos, info = fontes.microfone(args.dispositivo, args.segundos)
        print(f"[entrada] {info.nome} @ {info.fs_efetiva:.0f} Hz, latência {info.latencia_s * 1000:.0f} ms", file=sys.stderr)

    proc = Processador(fs, args.instrumento)
    jogo = Jogo(rep, args.comando, args.alvo)
    ao_vivo = not (args.simular or args.arquivo)
    for bloco in blocos:
        proc.alimentar(bloco)
        for ev in jogo.atualizar(proc.notas, proc.tempo):
            print(_linha(ev, args.json), flush=True)
            if ao_vivo and not args.mudo:
                _som_do_evento(ev, rep, fs)
    proc.finalizar()
    for ev in jogo.atualizar(proc.notas, proc.tempo):
        print(_linha(ev, args.json), flush=True)


if __name__ == "__main__":
    main()
