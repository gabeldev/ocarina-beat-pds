import numpy as np

from ocarina_beat.notas import midi_para_freq
from ocarina_beat.segmentador import Quadro, analisar, segmentar

FS = 48000
HOP = 512


def tom(midi, dur, amp=0.3, ataque=0.01):
    t = np.arange(int(dur * FS)) / FS
    env = np.minimum(1, t / ataque) * np.minimum(1, (dur - t) / ataque)
    return amp * env * np.sin(2 * np.pi * midi_para_freq(midi) * t)


def silencio(dur):
    return np.zeros(int(dur * FS))


def detectar(sinal, metodo="yin"):
    return segmentar(analisar(sinal, FS, metodo, hop=HOP), HOP / FS)


def test_sequencia_de_notas_distintas():
    sinal = np.concatenate([tom(74, .4), silencio(.1), tom(71, .4), silencio(.1), tom(69, .6)])
    notas = detectar(sinal)
    assert [n.midi for n in notas] == [74, 71, 69]
    assert abs(notas[0].duracao - 0.4) < 0.06
    assert abs(notas[0].inicio - 0.0) < 0.06


def test_notas_ligadas_sem_silencio():
    sinal = np.concatenate([tom(74, .4, ataque=.002), tom(77, .4, ataque=.002)])
    assert [n.midi for n in detectar(sinal)] == [74, 77]


def test_mesma_nota_repetida_com_queda_de_energia():
    sinal = np.concatenate([tom(72, .3), tom(72, .001 + 0.04, amp=0.02), tom(72, .3)])
    assert [n.midi for n in detectar(sinal)] == [72, 72]


def test_nota_sustentada_e_uma_so():
    assert [n.midi for n in detectar(tom(76, 1.0))] == [76]


def test_silencio_nao_gera_nota():
    assert detectar(silencio(1.0)) == []


def test_ruido_nao_gera_nota():
    rng = np.random.default_rng(0)
    assert detectar(0.05 * rng.standard_normal(FS)) == []


def test_quadro_isolado_com_outra_altura_e_ignorado():
    midis = [74] * 6 + [80] + [74] * 6
    quadros = [Quadro(i * HOP / FS, 0.2, m) for i, m in enumerate(midis)]
    assert [n.midi for n in segmentar(quadros, HOP / FS)] == [74]


def Q(midis, rms=None, hop=0.1):
    rms = rms or [0.2] * len(midis)
    return [Quadro(i * hop, r, m) for i, (m, r) in enumerate(zip(midis, rms))]


def test_tempos_consistentes_em_todos_os_fechamentos():
    # 4 quadros de 74 + 2 de silencio; e 4 quadros de 74 no fim do sinal: mesma duracao
    a = segmentar(Q([74] * 4 + [None] * 2), 0.1)[0]
    b = segmentar(Q([74] * 4), 0.1)[0]
    assert abs(a.inicio - b.inicio) < 1e-9 and abs(a.fim - b.fim) < 1e-9
    assert abs(a.duracao - 0.4) < 1e-9


def test_troca_de_nota_nao_perde_quadros_do_candidato():
    n = segmentar(Q([74] * 4 + [77] * 4), 0.1)
    assert abs(n[0].fim - n[1].inicio) < 1e-9
    assert abs(n[1].duracao - 0.4) < 1e-9


def test_glitch_apos_silencio_nao_atrapalha_ataque():
    n = segmentar(Q([None, None, 80, 74, 74, 74, None, None]), 0.1)
    assert [x.midi for x in n] == [74]


def test_reataque_com_vale_sem_f0():
    midis = [72] * 5 + [None] + [72] * 5
    rms = [0.3] * 5 + [0.02] + [0.3] * 5
    assert [x.midi for x in segmentar(Q(midis, rms), 0.1)] == [72, 72]


def test_cents_medio():
    n = segmentar(Q([74.2] * 4), 0.1)[0]
    assert abs(n.cents_medio - 20) < 1e-6
