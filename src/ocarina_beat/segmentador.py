"""Segmentação: sequência de quadros (rms, f0) -> eventos de nota.

Regras (todas em quadros de `hop` amostras):
- quadro sem f0 é silêncio; silêncio de pelo menos `min_silencio` quadros fecha a nota;
- uma nota nova só vale se persistir `min_quadros` quadros depois de silêncio, ou
  `min_quadros_transicao` quadros quando vem colada na anterior: na troca de dedilhado a
  flauta soa por ~50 ms uma nota intermediária, que não pode virar nota;
- histerese de afinação: enquanto o desvio em relação à nota atual for de até `histerese`
  semitons (0,6 = 60 cents), o quadro continua na mesma nota. Assim um sopro forte que leva
  a nota para a fronteira (ex.: Dó5 +48 cents) não a parte em Dó/Dó♯;
- notas repetidas (mesma altura) são separadas por uma queda de RMS: se o RMS cai
  abaixo de `queda` x o pico da nota e depois volta a subir acima de `retorno` x o pico,
  começa uma nova nota (reataque). A queda vale mesmo sem f0.

O `Segmentador` funciona quadro a quadro (tempo real); `segmentar` é o atalho em lote.
"""

from dataclasses import dataclass

import numpy as np

QUADROS_ATAQUE = 2  # primeiros quadros de uma nota (o "tu" começa baixo): não entram no rótulo
QUADROS_PARA_DIVULGAR = 6  # a nota em andamento só é exposta depois de ~65 ms, com o ataque já passado

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

    def __init__(self, hop_s, min_quadros=3, min_silencio=2, queda=0.35, retorno=0.6, histerese=0.6,
                 min_quadros_transicao=8):
        self.hop_s, self.min_quadros, self.min_silencio = hop_s, min_quadros, min_silencio
        self.min_quadros_transicao = min_quadros_transicao
        self.histerese = histerese
        self.queda, self.retorno = queda, retorno
        self.notas = []  # notas já fechadas
        self._atual = None  # {"midi", "frames", "pico"}
        self._cand = []  # quadros consecutivos com a mesma nota, ainda não confirmados
        self._sil = 0
        self._caiu = False

    @staticmethod
    def _estaveis(frames):
        return frames[QUADROS_ATAQUE:] if len(frames) > QUADROS_ATAQUE + 2 else frames

    def _nota(self, a):
        f = a["frames"]
        est = self._estaveis(f)
        desvios = [(q.midi - a["midi"]) * 100 for q in est]
        return NotaDetectada(a["midi"], f[0].t - self.hop_s / 2, f[-1].t + self.hop_s / 2, float(np.mean(desvios)))

    def _rotular(self, a):
        """A nota é batizada pela mediana dos quadros depois do ataque, não pelos primeiros."""
        a["midi"] = int(round(float(np.median([q.midi for q in self._estaveis(a["frames"])]))))

    def _fechar(self):
        a, self._atual = self._atual, None
        if a and len(a["frames"]) >= self.min_quadros:
            nota = self._nota(a)
            self.notas.append(nota)
            return nota
        return None

    def _abrir(self, frames):
        a = {"midi": int(round(frames[0].midi)), "frames": list(frames), "pico": max(q.rms for q in frames)}
        self._rotular(a)
        return a

    @property
    def atual(self):
        """Nota em andamento (já confirmada), com o fim até o último quadro; ou None."""
        a = self._atual
        return self._nota(a) if a and len(a["frames"]) >= max(self.min_quadros, QUADROS_PARA_DIVULGAR) else None

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
        # enquanto a nota é jovem (ataque se acomodando), aceita até 1 semitom; depois, a histerese
        tol = 1.0 if a and len(a["frames"]) < QUADROS_PARA_DIVULGAR else self.histerese
        if a and abs(q.midi - a["midi"]) <= tol:
            m = a["midi"]  # continua a mesma nota
        if a and m == a["midi"]:
            self._cand = []
            if self._caiu and q.rms > self.retorno * a["pico"]:  # reataque: nova nota, mesma altura
                fechadas.append(self._fechar())
                self._atual, self._caiu = self._abrir([q]), False
            else:
                a["frames"].append(q)
                a["pico"] = max(a["pico"], q.rms)
                self._rotular(a)
            return [n for n in fechadas if n]
        # nota diferente da atual (ou nenhuma): precisa persistir alguns quadros
        c = self._cand
        # depois de silêncio, candidatos até 1 semitom do primeiro são o ataque se acomodando (o "tu"
        # começa baixo; o rótulo sai da mediana). Colada na nota anterior, só o mesmo semitom: a nota
        # de passagem da troca de dedos não pode se juntar à nota seguinte
        if a:
            mesma = c and int(round(c[0].midi)) == m
        else:
            mesma = c and abs(q.midi - c[0].midi) <= 1.0
        self._cand = c + [q] if mesma else [q]
        exigido = self.min_quadros_transicao if a else self.min_quadros
        if len(self._cand) >= exigido:
            fechadas.append(self._fechar())
            self._atual, self._caiu, self._cand = self._abrir(self._cand), False, []
        return [n for n in fechadas if n]

    def finalizar(self):
        """Fecha a nota em andamento (fim do sinal)."""
        n = self._fechar()
        return [n] if n else []


def segmentar(quadros, hop_s, **kw):  # noqa: D103
    """Converte quadros em notas, em lote. `hop_s` é o passo entre quadros em segundos."""
    s = Segmentador(hop_s, **kw)
    for q in quadros:
        s.alimentar(q)
    s.finalizar()
    return s.notas
