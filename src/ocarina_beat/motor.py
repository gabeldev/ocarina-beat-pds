"""Motor em fluxo: blocos de áudio -> quadros -> notas, com a mesma lógica para
microfone, arquivo e sinal sintético (só muda quem entrega os blocos)."""

import numpy as np

from .estimador import METODOS
from .instrumento import INSTRUMENTOS, PADRAO
from .segmentador import Segmentador, medir_quadro


class Processador:
    def __init__(self, fs, instrumento=PADRAO, metodo="yin", janela=2048, hop=512, **kw_segmentador):
        ins = INSTRUMENTOS[instrumento]
        self.fs, self.janela, self.hop = fs, janela, hop
        self.fmin, self.fmax = ins.fmin, ins.fmax
        self.estimador = METODOS[metodo]
        self.segmentador = Segmentador(hop / fs, **kw_segmentador)
        self.quadros = []
        self._buf = np.zeros(0)
        self._n0 = 0  # índice global da primeira amostra de _buf

    @property
    def tempo(self):
        """Instante (s) do fim do último quadro processado."""
        return (self._n0 + self.janela - self.hop + self.janela) / self.fs if self.quadros else 0.0

    @property
    def notas(self):
        """Notas fechadas mais a nota em andamento, se houver."""
        a = self.segmentador.atual
        return self.segmentador.notas + ([a] if a else [])

    def alimentar(self, x):
        """Consome um bloco mono; devolve os quadros novos."""
        self._buf = np.concatenate([self._buf, np.asarray(x, dtype=float)])
        novos = []
        while len(self._buf) >= self.janela:
            t = (self._n0 + self.janela / 2) / self.fs
            q = medir_quadro(self._buf[: self.janela], self.fs, t, self.estimador, self.fmin, self.fmax)
            self.segmentador.alimentar(q)
            novos.append(q)
            self._buf = self._buf[self.hop :]
            self._n0 += self.hop
        self.quadros += novos
        return novos

    def finalizar(self):
        self.segmentador.finalizar()
        return self.segmentador.notas
