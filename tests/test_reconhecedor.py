from pathlib import Path

import pytest

from ocarina_beat.reconhecedor import carregar_repertorio, reconhecer
from ocarina_beat.segmentador import NotaDetectada

REP = Path(__file__).parent.parent / "repertorio"
pytestmark = pytest.mark.skipif(not list(REP.glob("*.json")), reason="repertório local ausente")


def tocar(cancao, n=None, escala=0.5, t0=1.0, jitter=None, ate=None):
    """Gera as notas detectadas de uma canção como se tocada (ataques por IOI = beats*escala)."""
    notas, t = [], t0
    for i, a in enumerate(cancao["notes"][: n or len(cancao["notes"])]):
        d = a["beats"] * escala * (jitter[i] if jitter else 1)
        notas.append(NotaDetectada(a["midi"], t, t + d * 0.9, 0.0))
        t += d
    return notas


@pytest.fixture(scope="module")
def rep():
    return carregar_repertorio(REP)


def test_cada_cancao_e_reconhecida_pela_propria_execucao(rep):
    for c in rep:
        r = reconhecer(tocar(c), rep)
        assert r is not None and r.id == c["id"], c["id"]


def test_so_o_comeco_basta(rep):
    for c in rep:
        r = reconhecer(tocar(c, n=c["reconhecer_primeiras"]), rep)
        assert r is not None and r.id == c["id"]


def test_uma_nota_a_menos_nao_reconhece(rep):
    for c in rep:
        assert reconhecer(tocar(c, n=c["reconhecer_primeiras"] - 1), rep) is None


def test_andamento_diferente(rep):
    for c in rep:
        for escala in (0.3, 1.0):
            assert reconhecer(tocar(c, escala=escala), rep).id == c["id"]


def test_nota_errada_rejeita(rep):
    c = rep[0]
    notas = tocar(c, n=c["reconhecer_primeiras"])
    notas[2].midi += 1
    r = reconhecer(notas, rep)
    assert r is None or r.id != c["id"]


def test_ritmo_muito_errado_rejeita(rep):
    c = next(x for x in rep if x["id"] == "epona_song")
    n = c["reconhecer_primeiras"]
    assert reconhecer(tocar(c, n=n, jitter=[1, 3, 0.3, 1, 1, 1][:n]), rep) is None


def test_notas_soltas_antes(rep):
    c = rep[1]
    extra = [NotaDetectada(70, 0.0, 0.2, 0.0)]
    r = reconhecer(extra + tocar(c, t0=1.0), rep)
    assert r.id == c["id"]


def test_pausa_longa_quebra_sequencia(rep):
    c = rep[1]
    notas = tocar(c)
    for x in notas[4:]:
        x.inicio += 10
        x.fim += 10
    assert reconhecer(notas, rep) is None


def _sintetizar(cancao, fs=48000, escala=0.4, gap=0.04, ruido=0.0, seed=0):
    import numpy as np

    from ocarina_beat.notas import midi_para_freq

    partes = []
    for a in cancao["notes"]:
        d = a["beats"] * escala
        t = np.arange(int((d - gap) * fs)) / fs
        env = np.minimum(1, t / 0.015) * np.minimum(1, (d - gap - t) / 0.015)
        partes.append(0.3 * env * np.sin(2 * np.pi * midi_para_freq(a["midi"]) * t))
        partes.append(np.zeros(int(gap * fs)))
    x = np.concatenate([np.zeros(fs // 2)] + partes + [np.zeros(fs // 2)])
    return x + ruido * np.random.default_rng(seed).standard_normal(len(x))


@pytest.mark.parametrize("ruido", [0.0, 0.01])
def test_ponta_a_ponta_sintetico(rep, ruido):
    from ocarina_beat.segmentador import analisar, segmentar

    for c in rep:
        x = _sintetizar(c, ruido=ruido)
        notas = segmentar(analisar(x, 48000, "yin", hop=512), 512 / 48000)
        r = reconhecer(notas, rep)
        assert r is not None and r.id == c["id"], (c["id"], [n.midi for n in notas])



def test_nota_alta_ainda_conta_como_a_esperada():
    from ocarina_beat.reconhecedor import bate

    do5_alto = NotaDetectada(73, 0, 1, -45.0)  # 72,55: lida como Dó#5 -45 cents
    assert bate(do5_alto, 72)
    assert not bate(NotaDetectada(74, 0, 1, 0.0), 72)  # um tom inteiro acima não conta
    assert not bate(NotaDetectada(73, 0, 1, 0.0), 72)  # Dó#5 afinado não conta como Dó5


def test_reconhece_cancao_tocada_desafinada(rep):
    c = rep[0]
    notas = tocar(c, n=c["reconhecer_primeiras"])
    for i, x in enumerate(notas):  # todas ~45 cents altas, algumas lidas como o semitom de cima
        if i % 2:
            x.midi, x.cents_medio = x.midi + 1, -55.0
        else:
            x.cents_medio = 45.0
    r = reconhecer(notas, rep)
    assert r is not None and r.id == c["id"]
