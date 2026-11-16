"""Gera repertorio/*.json a partir dos MIDIs em repertorio/referencias/.

Uso: python experimentos/gerar_repertorio.py
Os MIDIs e os JSONs ficam só localmente (a pasta repertorio/ não vai para o Git).
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from ocarina_beat.notas import nome_nota  # noqa: E402
from ocarina_beat.repertorio import ler_notas, para_cancao, salvar  # noqa: E402

REF = RAIZ / "repertorio" / "referencias"
PREFIXO = "Nintendo 64 (SoundFont MIDI)_The Legend of Zelda - Ocarina of Time_"

# (id, nome, arquivo, trilha, canal, notas do início que bastam para reconhecer, fatia [ini, fim) ou None)
CANCOES = [
    ("title_theme", "Title Theme", "001 - Title Theme.mid", 2, 1, 6, (0, 16)),  # corta antes de a abertura se repetir
    ("sarias_song", "Saria's Song", "055 - Ocarina “Saria’s Song”.mid", 4, 3, 6, None),
    ("zeldas_lullaby", "Zelda's Lullaby", "046 - Ocarina “Zelda’s Lullaby”.mid", 4, 3, 6, None),
    ("epona_song", "Epona's Song", "048 - Ocarina “Epona’s Song”.mid", 4, 3, 6, None),
    ("song_of_time", "Song of Time", "063 - Ocarina “Song of Time”.mid", 4, 3, 6, None),
    ("song_of_storms", "Song of Storms", "076 - Ocarina “Song of Storms”.mid", 4, 3, 6, None),
]


def conferir_prefixos(cancoes):
    """O começo de uma canção não pode ser o começo de outra (reconhecimento ambíguo)."""
    for a in cancoes:
        pa = tuple(n["midi"] for n in a["notes"][: a["reconhecer_primeiras"]])
        for b in cancoes:
            if a is b:
                continue
            pb = tuple(n["midi"] for n in b["notes"][: b["reconhecer_primeiras"]])
            k = min(len(pa), len(pb))
            if pa[:k] == pb[:k]:
                raise SystemExit(f"prefixo ambíguo entre {a['id']} e {b['id']}")


def main():
    geradas = []
    for id_, nome, arq, trilha, canal, n_rec, fatia in CANCOES:
        notas = ler_notas(REF / (PREFIXO + arq), trilha, canal)
        if fatia:
            notas = notas[fatia[0] : fatia[1]]
        c = para_cancao(notas, id_, nome, arq, reconhecer_primeiras=n_rec)
        geradas.append(c)
    conferir_prefixos(geradas)
    for c in geradas:
        salvar(c, RAIZ / "repertorio" / f"{c['id']}.json")
        seq = " ".join(nome_nota(n["midi"]) for n in c["notes"])
        print(f"{c['id']}: {len(c['notes'])} notas (reconhece pelas {c['reconhecer_primeiras']} primeiras), "
              f"{c['transposicao_oitavas']:+d} oitava(s)\n  {seq}")


if __name__ == "__main__":
    main()
