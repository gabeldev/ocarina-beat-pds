"""Conversão de melodias em MIDI para o formato de canção do repertório.

Formato (JSON): lista de notas MIDI com duração relativa em batidas, sem instantes
absolutos. A duração de cada nota é o intervalo até o início da seguinte (o último
valor é a duração da própria nota), arredondado para 1/12 de batida. Usar o
intervalo entre inícios evita que a articulação (nota curta seguida de pausa)
distorça o ritmo.
"""

import json
from dataclasses import dataclass

import mido

FA_MIN, FA_MAX = 69, 89  # A4..F6: faixa nominal de uma ocarina Alto C de 12 furos
GRADE = 12  # subdivisões de batida
DURACAO_MINIMA = 0.05  # batidas; descarta notas espúrias de poucos ticks


@dataclass
class Nota:
    midi: int
    inicio: float  # em batidas
    duracao: float  # em batidas


def ler_notas(caminho, trilha, canal):
    """Notas de um canal de uma trilha, em ordem de início."""
    mid = mido.MidiFile(caminho)
    ppq = mid.ticks_per_beat
    ativas, notas, t = {}, [], 0
    for msg in mid.tracks[trilha]:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0 and msg.channel == canal:
            ativas[msg.note] = t
        elif msg.type in ("note_off", "note_on") and msg.channel == canal and msg.note in ativas:
            ini = ativas.pop(msg.note)
            if (t - ini) / ppq >= DURACAO_MINIMA:
                notas.append(Nota(msg.note, ini / ppq, (t - ini) / ppq))
    return sorted(notas, key=lambda n: n.inicio)


def oitavas_para_caber(notas):
    """Menor número de oitavas a somar para a melodia caber em A4..F6."""
    menor, maior = min(n.midi for n in notas), max(n.midi for n in notas)
    for oit in range(-2, 4):
        if menor + 12 * oit >= FA_MIN and maior + 12 * oit <= FA_MAX:
            return oit
    raise ValueError(f"melodia ({menor}..{maior}) não cabe na faixa da ocarina")


def para_cancao(notas, id_, nome, fonte, transpor_oitavas=None, reconhecer_primeiras=None):
    """`reconhecer_primeiras`: quantas notas do início bastam para reconhecer a canção
    (None = a canção inteira). A melodia completa continua em `notes`."""
    if transpor_oitavas is None:
        transpor_oitavas = oitavas_para_caber(notas)
    saida = []
    for i, n in enumerate(notas):
        dur = notas[i + 1].inicio - n.inicio if i + 1 < len(notas) else n.duracao
        beats = max(round(dur * GRADE) / GRADE, 1 / GRADE)
        saida.append({"midi": n.midi + 12 * transpor_oitavas, "beats": round(beats, 4)})
    return {
        "schema_version": 1,
        "id": id_,
        "nome": nome,
        "fonte": fonte,
        "transposicao_oitavas": transpor_oitavas,
        "reference_a4_hz": 440.0,
        "reconhecer_primeiras": reconhecer_primeiras or len(saida),
        "notes": saida,
    }


def salvar(cancao, caminho):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(cancao, f, ensure_ascii=False, indent=2)
        f.write("\n")
