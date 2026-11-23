"""Motor em fluxo: blocos de áudio -> quadros -> notas, com a mesma lógica para
microfone, arquivo e sinal sintético (só muda quem entrega os blocos)."""

import numpy as np

from .estimador import METODOS
from .filtros import FiltroFluxo, projetar
from .instrumento import INSTRUMENTOS, PADRAO
from .segmentador import Segmentador, medir_quadro


MARGEM_RUIDO_DB = 10.0  # o tom precisa ficar pelo menos isso acima do ruído de fundo
QUADROS_PARA_PISO = 10  # quadros sem tom antes de confiar na estimativa do ruído


class Processador:
    def __init__(self, fs, instrumento=PADRAO, metodo="yin", janela=2048, hop=512, limiar_adaptativo=True,
                 filtro="fir", **kw_segmentador):
        ins = INSTRUMENTOS[instrumento]
        self.fs, self.janela, self.hop = fs, janela, hop
        self.fmin, self.fmax = ins.fmin, ins.fmax
        self.estimador = METODOS[metodo]
        self.segmentador = Segmentador(hop / fs, **kw_segmentador)
        # pré-filtragem passa-faixa (None, "iir" ou "fir"), aplicada a cada bloco antes do enquadramento
        self.filtro = FiltroFluxo(projetar(filtro, fs)) if filtro else None
        self.quadros = []
        self._buf = np.zeros(0)
        self._n0 = 0  # índice global da primeira amostra de _buf
        # piso de ruído (RMS dos quadros sem tom), média em dB que se adapta devagar
        self.limiar_adaptativo = limiar_adaptativo
        self.piso_db = None
        self._quadros_ruido = 0

    @property
    def limiar_db(self):
        """Nível mínimo (dBFS) para um quadro com tom contar como nota; None enquanto não há estimativa."""
        if self.piso_db is None or self._quadros_ruido < QUADROS_PARA_PISO:
            return None
        return self.piso_db + MARGEM_RUIDO_DB

    def _ajustar_por_ruido(self, q):
        db = 20 * np.log10(max(q.rms, 1e-9))
        if q.midi is None:
            # quadro sem tom: atualiza o piso (sobe devagar, desce rápido, para não "aprender" notas)
            if self.piso_db is None:
                self.piso_db = db
            else:
                peso = 0.02 if db > self.piso_db else 0.2
                self.piso_db += peso * (db - self.piso_db)
            self._quadros_ruido += 1
        elif self.limiar_adaptativo and self.limiar_db is not None and db < self.limiar_db:
            q.midi = None  # tom fraco demais perto do ruído da sala: trata como silêncio
        return q

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
        x = np.asarray(x, dtype=float)
        if self.filtro is not None:
            x = self.filtro(x)
        self._buf = np.concatenate([self._buf, x])
        novos = []
        while len(self._buf) >= self.janela:
            t = (self._n0 + self.janela / 2) / self.fs
            q = medir_quadro(self._buf[: self.janela], self.fs, t, self.estimador, self.fmin, self.fmax)
            q = self._ajustar_por_ruido(q)
            self.segmentador.alimentar(q)
            novos.append(q)
            self._buf = self._buf[self.hop :]
            self._n0 += self.hop
        self.quadros += novos
        return novos

    def finalizar(self):
        self.segmentador.finalizar()
        return self.segmentador.notas
