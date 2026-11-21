"""Instrumentos suportados: extensão (MIDI) e faixa de busca de f0 (Hz).

`midi_min`/`midi_max` delimitam as notas em que o repertório é colocado.
`fmin`/`fmax` são a faixa de busca dos estimadores, com folga em volta da extensão.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrumento:
    nome: str
    midi_min: int
    midi_max: int
    fmin: float
    fmax: float


INSTRUMENTOS = {
    # flauta doce soprano germânica em Dó: C5 (523 Hz) a D7 (2349 Hz) nominal;
    # o repertório fica em C5..A6, onde a emissão é mais estável para iniciante
    "flauta": Instrumento("Flauta doce soprano (Dó)", 72, 93, 480.0, 2400.0),
    # ocarina Alto C de 12 furos: A4 (440 Hz) a F6 (1397 Hz) nominal
    "ocarina": Instrumento("Ocarina Alto C 12 furos", 69, 89, 400.0, 1500.0),
}
PADRAO = "flauta"
