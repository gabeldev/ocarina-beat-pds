"""Reconhecimento: notas detectadas x começo de cada canção do repertório.

Uma canção é reconhecida quando as `reconhecer_primeiras` notas (consecutivas
entre as detectadas) correspondem às esperadas (até TOL_AFINACAO semitons de cada uma),
na ordem, e o ritmo é proporcional.
O ritmo usa o intervalo entre ataques (IOI) das N-1 primeiras notas e é conferido pela
estrutura: o que é longo na canção tem de ser claramente mais longo do que o curto, e nenhuma
relação entre dois intervalos pode ficar muito distorcida. O andamento não importa. A duração da
última nota do trecho não entra (o IOI dela depende da nota seguinte).
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Ritmo pela estrutura (tolerante a quem toca sem acompanhamento):
RAZAO_LONGO = 1.5  # na canção, um intervalo é "mais longo" que outro se for pelo menos 1,5x
MIN_RAZAO_TOCADA = 1.2  # tocado, o mais longo precisa durar pelo menos 1,2x o mais curto
MAX_DISTORCAO = 3.0  # nenhuma relação entre dois intervalos pode ficar distorcida mais que 3x
TOL_AFINACAO = 0.7  # semitons: a nota tocada vale como a esperada se estiver até 70 cents dela


def altura(nota):
    """Altura fracionária (MIDI + desvio médio) de uma nota detectada."""
    return nota.midi + nota.cents_medio / 100.0


def bate(nota, midi_esperado, tol=TOL_AFINACAO):
    """A nota tocada corresponde à esperada? Compara com a nota esperada, não com o arredondamento,
    para tolerar notas que saem altas ou baixas (ex.: Dó grave da flauta doce ~40 cents alto)."""
    return abs(altura(nota) - midi_esperado) <= tol
MAX_PAUSA_S = 5.0  # intervalo entre ataques acima disso quebra a sequência


@dataclass
class Resultado:
    id: str
    nome: str
    erro_ritmo: float  # maior erro relativo entre os intervalos (0 = perfeito)
    inicio: float  # s, ataque da primeira nota reconhecida
    fim: float  # s, fim da última nota reconhecida


def carregar_repertorio(pasta):
    return [json.loads(p.read_text()) for p in sorted(Path(pasta).glob("*.json"))]


def relacao_ok(t_a, t_b, e_a, e_b):
    """Dois intervalos tocados (t) respeitam a relação dos esperados (e)?"""
    rt, re = t_a / t_b, e_a / e_b
    if not (1 / MAX_DISTORCAO <= rt / re <= MAX_DISTORCAO):
        return False
    if re >= RAZAO_LONGO:
        return rt >= MIN_RAZAO_TOCADA
    if 1 / re >= RAZAO_LONGO:
        return 1 / rt >= MIN_RAZAO_TOCADA
    return True


def ritmo_ok(ioi, esperado):
    """Todas as relações entre pares de intervalos respeitam o ritmo da canção."""
    n = len(ioi)
    return all(relacao_ok(ioi[i], ioi[j], esperado[i], esperado[j]) for i in range(n) for j in range(i + 1, n))


def _erro_ritmo(notas, esperado):
    """Maior erro relativo dos IOIs normalizados; None se o ritmo é inviável."""
    n = len(esperado)
    if n < 2:
        return 0.0
    ioi = np.diff([x.inicio for x in notas])
    if np.any(ioi <= 0) or np.any(ioi > MAX_PAUSA_S):
        return None
    esp = np.array(esperado[:-1], dtype=float)
    return float(np.max(np.abs(ioi / ioi.sum() - esp / esp.sum()) / (esp / esp.sum())))


def reconhecer(notas, repertorio):
    """Devolve o melhor Resultado (menor erro de ritmo) ou None.

    Procura o trecho em qualquer posição de `notas`, para tolerar notas soltas antes.
    """
    melhor = None
    for c in repertorio:
        n = c["reconhecer_primeiras"]
        alvo = c["notes"][:n]
        midis = [a["midi"] for a in alvo]
        beats = [a["beats"] for a in alvo]
        for i in range(len(notas) - n + 1):
            trecho = notas[i : i + n]
            if not all(bate(t, m) for t, m in zip(trecho, midis)):
                continue
            e = _erro_ritmo(trecho, beats)
            if e is None or not ritmo_ok(np.diff([x.inicio for x in trecho]), beats[:-1]):
                continue
            if melhor is None or e < melhor.erro_ritmo:
                melhor = Resultado(c["id"], c["nome"], e, trecho[0].inicio, trecho[-1].fim)
    return melhor
