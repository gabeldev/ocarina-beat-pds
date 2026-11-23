"""E10 — efeito da pré-filtragem (sem filtro x IIR Butterworth x FIR Hamming) no mesmo áudio.

Uso:  PYTHONPATH=src .venv/bin/python experimentos/e10_filtros.py [--sinteticos]

Usa as sessões gravadas em dados/brutos/ (gravador.py). Sem gravações (ou com --sinteticos),
usa sinais sintéticos: notas da flauta com zumbido de rede (60/120 Hz) e ruído grave tipo ventilador.
Saída: tabela no terminal e dados/resultados/e10_filtros.csv.

Métricas por arquivo e por filtro:
- piso_db: piso de ruído estimado nos trechos sem tom (dBFS);
- notas: notas detectadas; em silencio/fala/ruido, todas são falsas (falsas_min = por minuto);
- desvio_cents: desvio padrão da afinação dentro das notas (estabilidade da estimativa);
- reconhecida: canção reconhecida no modo livre (sessões de canção);
- ms_por_s: custo de processamento (ms por segundo de áudio).
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from ocarina_beat import audio  # noqa: E402
from ocarina_beat.filtros import projetar  # noqa: E402
from ocarina_beat.jogo import Jogo  # noqa: E402
from ocarina_beat.motor import Processador  # noqa: E402
from ocarina_beat.reconhecedor import carregar_repertorio  # noqa: E402

FILTROS = [None, "iir", "fir"]


def sessoes_gravadas():
    for meta in sorted((RAIZ / "dados" / "brutos").glob("*/*.json")):
        d = json.loads(meta.read_text())
        fs, x = wavfile.read(meta.with_suffix(".wav"))
        yield d["id"], d["tipo"], d.get("alvo"), float(fs), x.astype(float)


def sessoes_sinteticas(rep):
    rng = np.random.default_rng(0)
    fs = audio.FS
    t = np.arange(fs * 6) / fs
    zumbido = 0.05 * np.sin(2 * np.pi * 60 * t) + 0.03 * np.sin(2 * np.pi * 120 * t)
    grave = np.convolve(rng.standard_normal(len(t)), np.ones(200) / 200, mode="same") * 0.6  # ruído grave
    chiado = 0.01 * rng.standard_normal(len(t))
    fundo = zumbido + grave + chiado
    yield "sint_silencio", "silencio", None, fs, fundo
    yield "sint_fala_grave", "fala", None, fs, fundo + 0.1 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 3 * t) > 0)
    for c in rep[:3]:
        x = np.concatenate([np.zeros(fs // 2), audio.cancao(c, 100), np.zeros(fs)])
        n = len(x)
        yield f"sint_{c['id']}", "cancao", c["id"], fs, x + np.resize(fundo, n)


def rodar(x, fs, filtro, rep):
    p = Processador(fs, filtro=filtro)
    j = Jogo(rep, "livre") if rep else None
    ev = []
    t0 = time.perf_counter()
    for i in range(0, len(x), 512):
        p.alimentar(x[i : i + 512])
        if j:
            ev += j.atualizar(p.notas, p.tempo)
    notas = p.finalizar()
    custo = (time.perf_counter() - t0) * 1000 / (len(x) / fs)
    desvios = [q.midi for q in p.quadros if q.midi is not None]
    return {
        "piso_db": round(p.piso_db, 1) if p.piso_db is not None else None,
        "notas": len(notas),
        "desvio_cents": round(float(np.std([(m - round(m)) * 100 for m in desvios])), 1) if desvios else None,
        "reconhecida": ",".join(e.dados["id"] for e in ev if e.tipo == "reconhecida"),
        "ms_por_s": round(custo, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sinteticos", action="store_true", help="usa sinais sintéticos mesmo havendo gravações")
    args = ap.parse_args()
    rep = carregar_repertorio(RAIZ / "repertorio")
    fontes = list(sessoes_gravadas())
    if args.sinteticos or not fontes:
        print("(sem gravações em dados/brutos/: usando sinais sintéticos)\n" if not fontes else "")
        fontes = list(sessoes_sinteticas(rep))

    for tipo in ("iir", "fir"):
        p = projetar(tipo, 48000)
        g = p.resposta([60, 120, 400, 523.25, 1760, 5000, 12000])
        print(f"{tipo.upper()}: ganho dB em 60/120/400/523/1760/5000/12000 Hz = {np.round(g, 1).tolist()} | "
              f"atraso ≈ {p.atraso_amostras() / 48:.2f} ms | estável: {p.estavel()}")
    print()

    linhas = []
    cab = f"{'arquivo':<28}{'tipo':<9}{'filtro':<6}{'piso dB':>8}{'notas':>6}{'falsas/min':>11}{'desvio ct':>10}{'ms/s':>6}  reconhecida"
    print(cab)
    print("-" * len(cab))
    for nome, tipo, alvo, fs, x in fontes:
        for f in FILTROS:
            r = rodar(x, fs, f, rep)
            dur_min = len(x) / fs / 60
            falsas = round(r["notas"] / dur_min, 1) if tipo in ("silencio", "fala", "ruido") else None
            linha = {"arquivo": nome, "tipo": tipo, "alvo": alvo, "filtro": f or "nenhum", **r, "falsas_min": falsas}
            linhas.append(linha)
            print(f"{nome[:27]:<28}{tipo:<9}{(f or '-'):<6}{str(r['piso_db']):>8}{r['notas']:>6}"
                  f"{'' if falsas is None else falsas:>11}{str(r['desvio_cents']):>10}{r['ms_por_s']:>6}  {r['reconhecida']}")
    saida = RAIZ / "dados" / "resultados"
    saida.mkdir(parents=True, exist_ok=True)
    with open(saida / "e10_filtros.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print(f"\nCSV: {(saida / 'e10_filtros.csv').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
