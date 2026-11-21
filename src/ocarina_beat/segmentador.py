"""Segmentação: sequência de quadros (rms, f0) -> eventos de nota.

Regras (todas em quadros de `hop` amostras):
- quadro sem f0 é silêncio; silêncio de pelo menos `min_silencio` quadros fecha a nota;
- mudança de nota MIDI só vale se persistir `min_quadros` quadros (ignora glitches);
- notas repetidas (mesma altura) são separadas por uma queda de RMS: se o RMS cai
  abaixo de `queda` x o pico da nota e depois volta a subir acima de `retorno` x o pico,
  começa uma nova nota (reataque). A queda vale mesmo sem f0.

O `Segmentador` funciona quadro a quadro (tempo real); `segmentar` é o atalho em lote.
"""

from dataclasses import dataclass

import numpy as np

from .estimador import METODOS, rms
from .instrumento import INSTRUMENTOS, PADRAO
from .notas import freq_para_midi


@dataclass
class Quadro:
    t: float  # tempo do centro da janela (s)
    rms: float
    midi: float | None  # MIDI fracionário, None se sem tom


@dataclass
class NotaDetectada:
    midi: int
    inicio: float  # s
    fim: float  # s
    cents_medio: float  # desvio médio em relação à nota inteira

    @property
    def duracao(self):
        return self.fim - self.inicio


def medir_quadro(seg, fs, t, estimador, fmin, fmax):
    """Estima o f0 de uma janela e devolve o Quadro."""
    f0, _ = estimador(seg, fs, fmin, fmax)
    return Quadro(t, rms(seg), None if f0 is None else freq_para_midi(f0))


def analisar(x, fs, metodo="yin", janela=2048, hop=512, fmin=None, fmax=None, instrumento=PADRAO):
    """Divide `x` em quadros e estima o f0 de cada um."""
    ins = INSTRUMENTOS[instrumento]
    fmin, fmax = fmin or ins.fmin, fmax or ins.fmax
    est = METODOS[metodo]
    return [
        medir_quadro(x[i : i + janela], fs, (i + janela / 2) / fs, est, fmin, fmax)
        for i in range(0, len(x) - janela + 1, hop)
    ]


class Segmentador:
    """Máquina de estados que transforma quadros em notas, um quadro por vez.

    Cada quadro cobre [t - hop/2, t + hop/2]; início e fim da nota seguem essa convenção.
    """

    def __init__(self, hop_s, min_quadros=3, min_silencio=2, queda=0.35, retorno=0.6):
        self.hop_s, self.min_quadros, self.min_silencio = hop_s, min_quadros, min_silencio
        self.queda, self.retorno = queda, retorno
        self.notas = []  # notas já fechadas
        self._atual = None  # {"midi", "frames", "pico"}
        self._cand = []  # quadros consecutivos com a mesma nota, ainda não confirmados
        self._sil = 0
        self._caiu = False

    def _nota(self, a):
        f = a["frames"]
        desvios = [(q.midi - a["midi"]) * 100 for q in f]
        return NotaDetectada(a["midi"], f[0].t - self.hop_s / 2, f[-1].t + self.hop_s / 2, float(np.mean(desvios)))

    def _fechar(self):
        a, self._atual = self._atual, None
        if a and len(a["frames"]) >= self.min_quadros:
            nota = self._nota(a)
            self.notas.append(nota)
            return nota
        return None

    @staticmethod
    def _abrir(frames):
        return {"midi": int(round(frames[0].midi)), "frames": list(frames), "pico": max(q.rms for q in frames)}

    @property
    def atual(self):
        """Nota em andamento (já confirmada), com o fim até o último quadro; ou None."""
        a = self._atual
        return self._nota(a) if a and len(a["frames"]) >= self.min_quadros else None

    def alimentar(self, q):
        """Processa um quadro; devolve as notas que fecharam neste quadro."""
        fechadas = []
        a = self._atual
        # a queda de energia vale mesmo sem f0 (o vale do reataque costuma perder a periodicidade)
        if a and q.rms < self.queda * a["pico"]:
            self._caiu = True
        if q.midi is None:
            self._sil += 1
            self._cand = []
            if a and self._sil >= self.min_silencio:
                fechadas.append(self._fechar())
                self._caiu = False
            return [n for n in fechadas if n]
        self._sil = 0
        m = int(round(q.midi))
        if a and m == a["midi"]:
            self._cand = []
            if self._caiu and q.rms > self.retorno * a["pico"]:  # reataque: nova nota, mesma altura
                fechadas.append(self._fechar())
                self._atual, self._caiu = self._abrir([q]), False
            else:
                a["frames"].append(q)
                a["pico"] = max(a["pico"], q.rms)
            return [n for n in fechadas if n]
        # nota diferente da atual (ou nenhuma): precisa persistir min_quadros
        c = self._cand
        self._cand = c + [q] if c and int(round(c[0].midi)) == m else [q]
        if len(self._cand) >= self.min_quadros:
            fechadas.append(self._fechar())
            self._atual, self._caiu, self._cand = self._abrir(self._cand), False, []
        return [n for n in fechadas if n]

    def finalizar(self):
        """Fecha a nota em andamento (fim do sinal)."""
        n = self._fechar()
        return [n] if n else []


def segmentar(quadros, hop_s, **kw):
    """Converte quadros em notas, em lote. `hop_s` é o passo entre quadros em segundos."""
    s = Segmentador(hop_s, **kw)
    for q in quadros:
        s.alimentar(q)
    s.finalizar()
    return s.notas
