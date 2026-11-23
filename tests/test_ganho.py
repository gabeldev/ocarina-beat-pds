import numpy as np

from ocarina_beat.ganho import ControleGanho
from ocarina_beat.motor import Processador
from ocarina_beat.notas import midi_para_freq
from ocarina_beat.segmentador import Quadro, segmentar

FS = 48000


class VolumeFalso:
    def __init__(self, v):
        self.v, self.escritas = v, []

    def ler(self):
        return self.v

    def escrever(self, v):
        self.v = v
        self.escritas.append(v)


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def tom(amp, n=512, f=880.0):
    return amp * np.sin(2 * np.pi * f * np.arange(n) / FS)


def test_estalo_ao_abrir_o_microfone_e_ignorado():
    vol, rel = VolumeFalso(0.5), Relogio()
    g = ControleGanho(vol, rel)
    for _ in range(3):
        rel.t += 0.05
        assert g.observar(tom(1.0), True) is None
    assert vol.escritas == []


def test_saturacao_baixa_o_volume():
    vol, rel = VolumeFalso(0.5), Relogio()
    g = ControleGanho(vol, rel)
    rel.t += 1.0  # depois do aquecimento
    assert g.observar(tom(1.0), True) is None  # um bloco só não basta
    rel.t += 0.01
    mud = g.observar(tom(1.0), True)
    assert mud["motivo"] == "saturacao" and abs(vol.v - 0.4) < 1e-9


def test_espera_o_efeito_antes_de_mudar_de_novo():
    vol, rel = VolumeFalso(0.5), Relogio()
    g = ControleGanho(vol, rel)
    rel.t += 1.0
    g.observar(tom(1.0), True)
    g.observar(tom(1.0), True)
    for _ in range(5):
        rel.t += 0.05
        assert g.observar(tom(1.0), True) is None  # ainda dentro da espera
    assert len(vol.escritas) == 1


def test_tom_fraco_por_um_tempo_sobe_o_volume():
    vol, rel = VolumeFalso(0.3), Relogio()
    g = ControleGanho(vol, rel)
    mud = None
    for _ in range(300):
        rel.t += 0.0107
        mud = mud or g.observar(tom(0.005), True)  # ~ -49 dBFS
    assert mud and mud["motivo"] == "fraco" and vol.v > 0.3


def test_ruido_no_silencio_nao_mexe_no_volume():
    vol, rel = VolumeFalso(0.3), Relogio()
    g = ControleGanho(vol, rel)
    rng = np.random.default_rng(0)
    for _ in range(500):
        rel.t += 0.0107
        assert g.observar(0.003 * rng.standard_normal(512), False) is None
    assert vol.escritas == []


def test_respeita_os_limites():
    vol, rel = VolumeFalso(0.06), Relogio()
    g = ControleGanho(vol, rel)
    for _ in range(20):
        rel.t += 1.0
        g.observar(tom(1.0), True)
        g.observar(tom(1.0), True)
    assert vol.v >= 0.05


def test_sem_controle_de_volume_fica_desligado():
    g = ControleGanho(volume=None)
    g.volume = None
    g.ativo = False
    assert g.observar(tom(1.0), True) is None


# --- histerese de afinação ---
def test_nota_na_fronteira_nao_se_parte():
    # Dó5 tocado ~45-55 cents alto, oscilando na fronteira com Dó#5 (como na flauta real)
    midis = [72.45, 72.48, 72.52, 72.47, 72.55, 72.49, 72.53, 72.46] * 3
    quadros = [Quadro(i * 0.01, 0.2, m) for i, m in enumerate(midis)]
    assert [n.midi for n in segmentar(quadros, 0.01)] == [72]


def test_meio_tom_de_verdade_ainda_troca_de_nota():
    midis = [84.0] * 10 + [84.62] * 10  # Dó6 -> Dó#6 tocado 38 cents baixo
    quadros = [Quadro(i * 0.01, 0.2, m) for i, m in enumerate(midis)]
    assert [n.midi for n in segmentar(quadros, 0.01)] == [84, 85]


# --- limiar de silêncio adaptativo ---
def _sinal(ruido_amp, tom_amp, rng):
    n = FS
    ruido = ruido_amp * rng.standard_normal(3 * n)
    x = ruido.copy()
    t = np.arange(n) / FS
    x[n : 2 * n] += tom_amp * np.sin(2 * np.pi * midi_para_freq(81) * t)
    return x


def test_tom_fraco_perto_do_ruido_nao_vira_nota():
    # tom ~8 dB acima do ruído: o YIN sozinho aceitaria, o limiar adaptativo (10 dB) recusa
    # sem filtro, para isolar o efeito do limiar (o filtro sozinho já melhora a relação sinal-ruído)
    sem = Processador(FS, limiar_adaptativo=False, filtro=None)
    sem.alimentar(_sinal(0.02, 0.07, np.random.default_rng(1)))
    assert [n.midi for n in sem.finalizar()] == [81]
    com = Processador(FS, filtro=None)
    com.alimentar(_sinal(0.02, 0.07, np.random.default_rng(1)))
    assert com.finalizar() == []


def test_tom_bem_acima_do_ruido_vira_nota():
    rng = np.random.default_rng(1)
    p = Processador(FS)
    p.alimentar(_sinal(0.02, 0.3, rng))
    assert [n.midi for n in p.finalizar()] == [81]
