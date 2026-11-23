"""Controle automático do ganho do microfone (AGC), para o jogador não precisar mexer em nada.

Observa os blocos captados e ajusta o volume de entrada do sistema:
- saturação (picos >= LIMITE_SATURACAO em vários blocos seguidos) -> baixa um passo;
- notas fracas demais (nível do tom abaixo de NIVEL_FRACO_DBFS por um tempo) -> sobe um passo.
Só reage com tom presente (ou saturação), nunca ao ruído do silêncio.

No Linux com PipeWire o volume da fonte padrão é lido e escrito com `wpctl`.
Sem `wpctl` (outro sistema), o controle fica desligado e o jogo segue normalmente.
"""

import re
import shutil
import subprocess
import time

import numpy as np

LIMITE_SATURACAO = 0.98  # amplitude de pico considerada corte
BLOCOS_SATURADOS = 2  # quantos blocos saturados (dentro da janela) disparam a redução
JANELA_SATURACAO_S = 0.5
NIVEL_FRACO_DBFS = -38.0  # tom abaixo disso é fraco
TEMPO_FRACO_S = 2.0  # quanto tempo de tom fraco antes de subir
PASSO_DESCE, PASSO_SOBE = 0.8, 1.15
VOLUME_MIN, VOLUME_MAX = 0.05, 1.0
ESPERA_S = 0.7  # depois de mudar, espera o efeito antes de avaliar de novo
AQUECIMENTO_S = 0.5  # ignora o começo da captura (o microfone dá um estalo ao abrir)


class VolumeWpctl:
    """Volume da fonte de áudio padrão do PipeWire (0..1)."""

    ALVO = "@DEFAULT_AUDIO_SOURCE@"

    @staticmethod
    def disponivel():
        return shutil.which("wpctl") is not None

    def ler(self):
        saida = subprocess.run(["wpctl", "get-volume", self.ALVO], capture_output=True, text=True, timeout=2).stdout
        m = re.search(r"Volume:\s*([\d.]+)", saida)
        return float(m.group(1)) if m else None

    def escrever(self, v):
        subprocess.run(["wpctl", "set-volume", self.ALVO, f"{v:.3f}"], capture_output=True, timeout=2)


class ControleGanho:
    def __init__(self, volume=None, relogio=time.monotonic):
        if volume is None and VolumeWpctl.disponivel():
            volume = VolumeWpctl()
        self.volume = volume
        self.relogio = relogio
        self.atual = None
        if self.volume is not None:
            try:
                self.atual = self.volume.ler()
            except (OSError, subprocess.SubprocessError):
                self.atual = None
        self.ativo = self.atual is not None
        self._saturados = []  # instantes de blocos saturados
        self._fraco_desde = None
        self._espera_ate = self.relogio() + AQUECIMENTO_S

    def _mudar(self, fator, motivo):
        novo = float(np.clip(self.atual * fator, VOLUME_MIN, VOLUME_MAX))
        if abs(novo - self.atual) < 1e-3:
            return None  # já no limite
        try:
            self.volume.escrever(novo)
        except (OSError, subprocess.SubprocessError):
            self.ativo = False
            return None
        self.atual = novo
        self._espera_ate = self.relogio() + ESPERA_S
        self._saturados.clear()
        self._fraco_desde = None
        return {"volume": round(novo, 3), "motivo": motivo}

    def observar(self, bloco, tem_tom):
        """Recebe um bloco captado e se há tom nele; devolve {volume, motivo} quando mudou o ganho."""
        if not self.ativo:
            return None
        agora = self.relogio()
        if agora < self._espera_ate:
            return None
        x = np.asarray(bloco, dtype=float)
        if x.size == 0:
            return None
        if np.abs(x).max() >= LIMITE_SATURACAO:
            self._saturados = [t for t in self._saturados if agora - t <= JANELA_SATURACAO_S] + [agora]
            if len(self._saturados) >= BLOCOS_SATURADOS:
                return self._mudar(PASSO_DESCE, "saturacao")
            return None
        if tem_tom:
            nivel = 20 * np.log10(max(float(np.sqrt(np.mean((x - x.mean()) ** 2))), 1e-9))
            if nivel < NIVEL_FRACO_DBFS:
                if self._fraco_desde is None:
                    self._fraco_desde = agora
                elif agora - self._fraco_desde >= TEMPO_FRACO_S:
                    return self._mudar(PASSO_SOBE, "fraco")
            else:
                self._fraco_desde = None
        return None
