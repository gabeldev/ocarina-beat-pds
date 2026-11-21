"""Lógica do jogo: consome as notas detectadas e emite eventos.

Não toca em áudio nem tela; quem usa (CLI, Godot) recebe `Evento`s e decide o que
mostrar ou tocar. `Evento.para_json()` é o formato que irá para a interface 3D.

Modos:
- livre:   a cada atualização, testa se o final do histórico forma uma canção do repertório;
- aprender: confere nota a nota a execução de uma canção escolhida, completa.
"""

import json
from dataclasses import dataclass, field

import numpy as np

from .notas import nome_nota
from .reconhecedor import reconhecer

TOL_RITMO_APRENDER = 0.4  # erro relativo máximo de um intervalo em relação ao esperado
TIMEOUT_S = 6.0  # sem nova nota por esse tempo, a tentativa é considerada incompleta


@dataclass
class Evento:
    tipo: str  # nota | reconhecida | progresso | divergencia | completa | incompleta
    t: float
    dados: dict = field(default_factory=dict)

    def para_json(self):
        return json.dumps({"tipo": self.tipo, "t": round(self.t, 3), **self.dados}, ensure_ascii=False)


class Jogo:
    def __init__(self, repertorio, modo="livre", alvo=None, tol_ritmo=TOL_RITMO_APRENDER):
        self.rep = repertorio
        self.modo = modo
        self.tol = tol_ritmo
        self.alvo = next(c for c in repertorio if c["id"] == alvo) if modo == "aprender" else None
        self.aprendidas = set()
        self._vistas = 0  # quantas notas já geraram evento "nota"
        self._corte = -1.0  # no modo livre, só notas com início depois disso entram no histórico
        self._reiniciar()

    def _reiniciar(self):
        self._idx = 0
        self._onsets = []

    def atualizar(self, notas, t):
        """`notas`: todas as notas até agora (fechadas + em andamento). Devolve os eventos novos."""
        ev = []
        for n in notas[self._vistas :]:
            ev.append(Evento("nota", n.inicio, {"midi": n.midi, "nome": nome_nota(n.midi), "cents": round(n.cents_medio, 1)}))
            if self.modo == "aprender":
                ev += self._conferir(n)
        self._vistas = len(notas)
        if self.modo == "livre":
            ev += self._livre(notas, t)
        elif self._idx and t - self._onsets[-1] > TIMEOUT_S:
            ev.append(Evento("incompleta", t, {"tocadas": self._idx, "total": len(self.alvo["notes"])}))
            self._reiniciar()
        return ev

    # --- modo livre ---
    def _livre(self, notas, t):
        hist = [n for n in notas if n.inicio > self._corte]
        r = reconhecer(hist, self.rep)
        if r is None:
            return []
        self._corte = hist[-1].inicio  # consome tudo até aqui, evita disparar duas vezes
        return [Evento("reconhecida", t, {"id": r.id, "nome": r.nome, "erro_ritmo": round(r.erro_ritmo, 3)})]

    # --- modo aprender ---
    def _divergir(self, n, tipo, **extra):
        esperada = self.alvo["notes"][self._idx]["midi"]
        ev = Evento("divergencia", n.inicio, {"motivo": tipo, "posicao": self._idx, "esperada": nome_nota(esperada), "tocada": nome_nota(n.midi), **extra})
        self._reiniciar()
        return ev

    def _conferir(self, n):
        notas = self.alvo["notes"]
        if n.midi != notas[self._idx]["midi"]:
            ev = self._divergir(n, "nota")
            # a nota errada pode ser o começo de uma nova tentativa
            return [ev] + (self._conferir(n) if n.midi == notas[0]["midi"] else [])
        k = len(self._onsets)  # notas já aceitas; esta é a de índice k
        if k >= 2:
            # escala (s/batida) dos intervalos já completos; confere o intervalo que acabou de fechar
            ioi = np.diff(self._onsets)
            escala = ioi.sum() / sum(a["beats"] for a in notas[: k - 1])
            esperado = notas[k - 1]["beats"] * escala
            tocado = n.inicio - self._onsets[-1]
            if abs(tocado - esperado) / esperado > self.tol:
                return [self._divergir(n, "ritmo", esperado_s=round(esperado, 2), tocado_s=round(float(tocado), 2))]
        self._onsets.append(n.inicio)
        self._idx += 1
        if self._idx == len(notas):
            self.aprendidas.add(self.alvo["id"])
            self._reiniciar()
            return [Evento("completa", n.inicio, {"id": self.alvo["id"], "nome": self.alvo["nome"]})]
        return [Evento("progresso", n.inicio, {"tocadas": self._idx, "total": len(notas)})]
