"""Reconhecimento: notas detectadas x começo de cada canção do repertório.

Uma canção é reconhecida quando as `reconhecer_primeiras` notas (consecutivas
entre as detectadas) têm a mesma altura MIDI, na ordem, e o ritmo é proporcional.
O ritmo usa o intervalo entre ataques (IOI) das N-1 primeiras notas, normalizado
pela soma, então tocar mais rápido ou mais devagar não importa. A duração da
última nota do trecho não entra (o IOI dela depende da nota seguinte).
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

TOL_RITMO = 0.35  # erro relativo máximo por intervalo, após normalização
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


def reconhecer(notas, repertorio, tol=TOL_RITMO):
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
            if [t.midi for t in trecho] != midis:
                continue
            e = _erro_ritmo(trecho, beats)
            if e is None or e > tol:
                continue
            if melhor is None or e < melhor.erro_ritmo:
                melhor = Resultado(c["id"], c["nome"], e, trecho[0].inicio, trecho[-1].fim)
    return melhor
