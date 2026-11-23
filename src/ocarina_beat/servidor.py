"""Serviço UDP: roda o jogo e conversa com a interface (Godot) em JSON, uma mensagem por datagrama.

    python -m ocarina_beat.servidor [--eventos 9000] [--comandos 9001]

Protocolo em jogo/PROTOCOLO.md. Eventos saem para 127.0.0.1:<eventos>;
comandos chegam em 127.0.0.1:<comandos>.
"""

import argparse
import json
import socket
import time
from pathlib import Path

import numpy as np

from . import fontes
from .instrumento import INSTRUMENTOS, PADRAO
from .jogo import Jogo
from .motor import Processador
from .notas import nome_nota
from .reconhecedor import carregar_repertorio

INTERVALO_NIVEL_S = 0.05  # no máximo 20 eventos "nivel" por segundo


class Servidor:
    def __init__(self, rep, instrumento=PADRAO, porta_eventos=9000, porta_comandos=9001, host="127.0.0.1"):
        self.rep, self.instrumento = rep, instrumento
        self.por_id = {c["id"]: c for c in rep}
        self.destino = (host, porta_eventos)
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.bind((host, porta_comandos))
        self.rx.setblocking(False)
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.porta_comandos = self.rx.getsockname()[1]
        self.modo, self.alvo = "livre", None
        self.jogo = Jogo(rep, "livre")
        self.fonte = self.proc = None
        self._t_nivel = -1.0
        self.ativo = True

    # --- saída ---
    def enviar(self, tipo, **dados):
        msg = json.dumps({"tipo": tipo, **dados}, ensure_ascii=False)
        self.tx.sendto(msg.encode(), self.destino)

    def estado(self):
        self.enviar("estado", modo=self.modo, alvo=self.alvo, instrumento=self.instrumento,
                    ouvindo=self.fonte is not None, aprendidas=sorted(self.jogo.aprendidas))

    # --- comandos ---
    def _novo_jogo(self, modo, alvo=None):
        aprendidas = self.jogo.aprendidas
        self.modo, self.alvo = modo, alvo
        self.jogo = Jogo(self.rep, modo, alvo)
        self.jogo.aprendidas |= aprendidas
        if self.proc:  # recomeça o histórico de notas junto com o jogo
            self.proc = Processador(self.proc.fs, self.instrumento)
        self.estado()

    def _iniciar_fonte(self, fs, blocos):
        self.proc = Processador(fs, self.instrumento)
        self.jogo = Jogo(self.rep, self.modo, self.alvo)
        self.fonte = iter(blocos)
        self._t_nivel = -1.0
        self.estado()

    def comando(self, msg):
        cmd = msg.get("cmd")
        try:
            if cmd == "livre":
                self._novo_jogo("livre")
            elif cmd == "aprender":
                if msg.get("id") not in self.por_id:
                    return self.enviar("erro", mensagem=f"canção desconhecida: {msg.get('id')!r}")
                self._novo_jogo("aprender", msg["id"])
            elif cmd == "simular":
                c = self.por_id.get(msg.get("id"))
                if c is None:
                    return self.enviar("erro", mensagem=f"canção desconhecida: {msg.get('id')!r}")
                fs, blocos = fontes.simulada(c, msg.get("bpm", 100), msg.get("ruido", 0.0))
                self._iniciar_fonte(fs, fontes.em_tempo_real(fs, blocos))
            elif cmd == "microfone":
                fs, blocos, _ = fontes.microfone(msg.get("dispositivo"))
                self._iniciar_fonte(fs, blocos)
            elif cmd == "parar":
                self.fonte = None
                self.estado()
            elif cmd == "estado":
                self.estado()
            elif cmd == "cancoes":
                self.enviar("cancoes", lista=[
                    {"id": c["id"], "nome": c["nome"], "notas": [nome_nota(n["midi"]) for n in c["notes"]],
                     "beats": [n["beats"] for n in c["notes"]], "reconhecer_primeiras": c["reconhecer_primeiras"]}
                    for c in self.rep])
            elif cmd == "sair":
                self.ativo = False
            else:
                self.enviar("erro", mensagem=f"comando desconhecido: {cmd!r}")
        except Exception as e:  # um comando ruim não derruba o serviço
            self.enviar("erro", mensagem=f"{type(e).__name__}: {e}")

    def _ler_comandos(self):
        while True:
            try:
                dados, _ = self.rx.recvfrom(65535)
            except BlockingIOError:
                return
            try:
                self.comando(json.loads(dados))
            except json.JSONDecodeError:
                self.enviar("erro", mensagem="JSON inválido")

    # --- laço principal ---
    def _passo(self):
        try:
            bloco = next(self.fonte)
        except StopIteration:
            self.proc.finalizar()
            for ev in self.jogo.atualizar(self.proc.notas, self.proc.tempo):
                self.enviar(ev.tipo, t=round(ev.t, 3), **ev.dados)
            self.fonte = None
            self.enviar("fim_audio")
            return self.estado()
        quadros = self.proc.alimentar(bloco)
        for ev in self.jogo.atualizar(self.proc.notas, self.proc.tempo):
            self.enviar(ev.tipo, t=round(ev.t, 3), **ev.dados)
        if quadros and quadros[-1].t - self._t_nivel >= INTERVALO_NIVEL_S:
            self._t_nivel = quadros[-1].t
            q = quadros[-1]
            self.enviar("nivel", t=round(q.t, 3), dbfs=round(20 * float(np.log10(max(q.rms, 1e-9))), 1),
                        midi=None if q.midi is None else round(q.midi, 2),
                        nome=None if q.midi is None else nome_nota(int(round(q.midi))))

    def executar(self, max_s=None):
        fim = None if max_s is None else time.time() + max_s
        self.estado()
        while self.ativo and (fim is None or time.time() < fim):
            self._ler_comandos()
            if self.fonte is not None:
                self._passo()
            else:
                time.sleep(0.01)

    def fechar(self):
        self.rx.close()
        self.tx.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eventos", type=int, default=9000)
    ap.add_argument("--comandos", type=int, default=9001)
    ap.add_argument("--repertorio", type=Path, default=Path(__file__).resolve().parents[2] / "repertorio")
    ap.add_argument("--instrumento", choices=sorted(INSTRUMENTOS), default=PADRAO)
    args = ap.parse_args(argv)
    rep = carregar_repertorio(args.repertorio)
    if not rep:
        raise SystemExit(f"repertório vazio em {args.repertorio} (rode experimentos/gerar_repertorio.py)")
    s = Servidor(rep, args.instrumento, args.eventos, args.comandos)
    print(f"Eventos -> 127.0.0.1:{args.eventos} | comandos <- 127.0.0.1:{args.comandos} (Ctrl+C para sair)")
    try:
        s.executar()
    except KeyboardInterrupt:
        pass
    finally:
        s.fechar()


if __name__ == "__main__":
    main()
