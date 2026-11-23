import numpy as np
import pytest

from ocarina_beat import audio
from ocarina_beat.jogo import Jogo
from ocarina_beat.motor import Processador
from ocarina_beat.segmentador import NotaDetectada, analisar, segmentar

FS = audio.FS

CANCAO = {
    "id": "teste", "nome": "Teste", "reconhecer_primeiras": 4,
    "notes": [{"midi": m, "beats": b} for m, b in [(74, 1), (77, 1), (79, 2), (77, 1), (74, 1)]],
}
OUTRA = {"id": "outra", "nome": "Outra", "reconhecer_primeiras": 4,
         "notes": [{"midi": m, "beats": 1} for m in (72, 76, 79, 83, 84)]}


def executar(jogo, midis_beats, escala=0.5, t0=1.0):
    """Alimenta o jogo nota a nota (como se o segmentador as confirmasse na hora)."""
    notas, ev, t = jogo.__dict__.setdefault("_h", []), [], t0
    for m, b in midis_beats:
        notas.append(NotaDetectada(m, t, t + b * escala * 0.9, 0.0))
        ev += jogo.atualizar(notas, t)
        t += b * escala
    return ev


def tipos(ev):
    return [e.tipo for e in ev if e.tipo != "nota"]


def test_aprender_completa():
    j = Jogo([CANCAO], "aprender", "teste")
    ev = executar(j, [(a["midi"], a["beats"]) for a in CANCAO["notes"]])
    assert tipos(ev)[-1] == "completa" and "divergencia" not in tipos(ev)
    assert "teste" in j.aprendidas


def test_aprender_nota_errada_reinicia():
    j = Jogo([CANCAO], "aprender", "teste")
    ev = executar(j, [(74, 1), (76, 1)])
    d = [e for e in ev if e.tipo == "divergencia"][0]
    assert d.dados["motivo"] == "nota" and d.dados["esperada"] == "F5" and d.dados["posicao"] == 1
    # depois do erro, recomeça do início e completa
    ev = executar(j, [(a["midi"], a["beats"]) for a in CANCAO["notes"]], t0=10)
    assert tipos(ev)[-1] == "completa"


def test_aprender_nota_errada_que_e_a_primeira_ja_conta():
    j = Jogo([CANCAO], "aprender", "teste")
    ev = executar(j, [(74, 1), (74, 1)])  # a segunda deveria ser F5; mas é D5, início válido
    assert tipos(ev) == ["progresso", "divergencia", "progresso"]


def test_aprender_ritmo_errado():
    # CANCAO: D5(1) F5(1) G5(2) F5(1) D5(1). A nota longa (G5) tocada curta inverte o ritmo
    j = Jogo([CANCAO], "aprender", "teste")
    ev = executar(j, [(74, 1), (77, 1), (79, 0.4), (77, 1)])
    d = [e for e in ev if e.tipo == "divergencia"]
    assert d and d[0].dados["motivo"] == "ritmo" and d[0].dados["posicao"] == 3


def test_aprender_tolera_ritmo_de_iniciante():
    # curtas um pouco desiguais e a longa só 1,5x mais longa: a estrutura está certa
    j = Jogo([CANCAO], "aprender", "teste")
    ev = executar(j, [(74, 1), (77, 1.6), (79, 2.4), (77, 1.2), (74, 1)])
    assert "divergencia" not in tipos(ev) and tipos(ev)[-1] == "completa"


def test_livre_reconhece_ritmo_de_iniciante():
    # tentativa real na flauta (Epona's Song): curtas desiguais, longa a mais longa
    ep = {"id": "ep", "nome": "Ep", "reconhecer_primeiras": 6,
          "notes": [{"midi": m, "beats": b} for m, b in [(86, .5), (83, .5), (81, 2), (86, .5), (83, .5), (81, 2)]]}
    j = Jogo([ep], "livre")
    inicios = [7.58, 8.35, 9.74, 11.87, 12.41, 13.16]
    notas = []
    ev = []
    for m, t in zip([86, 83, 81, 86, 83, 81], inicios):
        notas.append(NotaDetectada(m, t, t + 0.3, -30.0))
        ev += j.atualizar(notas, t)
    assert [e.dados["id"] for e in ev if e.tipo == "reconhecida"] == ["ep"]


def test_livre_recusa_notas_todas_iguais():
    ep = {"id": "ep", "nome": "Ep", "reconhecer_primeiras": 6,
          "notes": [{"midi": m, "beats": b} for m, b in [(86, .5), (83, .5), (81, 2), (86, .5), (83, .5), (81, 2)]]}
    j = Jogo([ep], "livre")
    ev = executar(j, [(86, 1), (83, 1), (81, 1), (86, 1), (83, 1), (81, 1)])
    assert "reconhecida" not in tipos(ev)


def test_aprender_timeout():
    j = Jogo([CANCAO], "aprender", "teste")
    executar(j, [(74, 1), (77, 1)])
    ev = j.atualizar([], 30.0)
    assert [e.tipo for e in ev] == ["incompleta"]


def test_livre_reconhece_e_nao_repete():
    j = Jogo([CANCAO, OUTRA], "livre")
    ev = executar(j, [(60, 1)] + [(a["midi"], a["beats"]) for a in CANCAO["notes"]])
    assert [e.dados["id"] for e in ev if e.tipo == "reconhecida"] == ["teste"]


def test_livre_melodia_desconhecida_nao_dispara():
    j = Jogo([CANCAO], "livre")
    assert "reconhecida" not in tipos(executar(j, [(74, 1), (77, 1), (77, 2), (74, 1), (74, 1)]))


def test_livre_duas_canções_seguidas():
    j = Jogo([CANCAO, OUTRA], "livre")
    seq = [(a["midi"], a["beats"]) for a in CANCAO["notes"][:4]] + [(m, 1) for m in (72, 76, 79, 83)]
    ev = executar(j, seq)
    assert [e.dados["id"] for e in ev if e.tipo == "reconhecida"] == ["teste", "outra"]


def test_evento_json():
    j = Jogo([CANCAO], "livre")
    ev = executar(j, [(74, 1)])
    assert '"tipo": "nota"' in ev[0].para_json() and '"nome": "D5"' in ev[0].para_json()


# --- áudio e motor ---
def test_motor_em_fluxo_igual_ao_lote():
    x = audio.cancao(CANCAO, bpm=100)
    x = np.concatenate([np.zeros(FS // 2), x, np.zeros(FS)])
    lote = segmentar(analisar(x, FS, hop=512), 512 / FS)
    p = Processador(FS, filtro=None)  # o lote não filtra; aqui só se compara fluxo x lote
    for i in range(0, len(x), 700):  # blocos de tamanho irregular
        p.alimentar(x[i : i + 700])
    fluxo = p.finalizar()
    assert [n.midi for n in fluxo] == [n.midi for n in lote] == [74, 77, 79, 77, 74]
    assert all(abs(a.inicio - b.inicio) < 1e-9 for a, b in zip(fluxo, lote))


@pytest.mark.parametrize("vibrato", [True, False])
def test_timbre_sintetico_e_detectado_nas_alturas_certas(vibrato):
    for m in range(72, 94):
        p = Processador(FS)
        p.alimentar(np.concatenate([np.zeros(FS // 4), audio.nota(m, 0.5, vibrato=vibrato), np.zeros(FS // 4)]))
        assert [n.midi for n in p.finalizar()] == [m], m


@pytest.mark.parametrize("bpm", [60, 100, 160])
def test_ponta_a_ponta_aprender_com_audio(bpm):
    x = np.concatenate([np.zeros(FS // 2), audio.cancao(CANCAO, bpm), np.zeros(FS)])
    p, j, ev = Processador(FS), Jogo([CANCAO], "aprender", "teste"), []
    for i in range(0, len(x), 512):
        p.alimentar(x[i : i + 512])
        ev += j.atualizar(p.notas, p.tempo)
    p.finalizar()
    ev += j.atualizar(p.notas, p.tempo)
    assert tipos(ev)[-1] == "completa", tipos(ev)


def test_ponta_a_ponta_livre_com_audio_e_ruido():
    x = np.concatenate([np.zeros(FS // 2), audio.cancao(CANCAO, 100), np.zeros(FS)])
    x = x + 0.01 * np.random.default_rng(1).standard_normal(len(x))
    p, j, ev = Processador(FS), Jogo([CANCAO, OUTRA], "livre"), []
    for i in range(0, len(x), 512):
        p.alimentar(x[i : i + 512])
        ev += j.atualizar(p.notas, p.tempo)
    assert [e.dados["id"] for e in ev if e.tipo == "reconhecida"] == ["teste"]


# --- repertório real (só roda onde o repertório local existe) ---
from pathlib import Path  # noqa: E402

from ocarina_beat.reconhecedor import carregar_repertorio  # noqa: E402

REP = Path(__file__).parent.parent / "repertorio"


def _rodar(rep, modo, alvo, cancao, bpm):
    x = np.concatenate([np.zeros(FS // 2), audio.cancao(cancao, bpm), np.zeros(FS)])
    x = x + 0.01 * np.random.default_rng(2).standard_normal(len(x))
    p, j, ev = Processador(FS), Jogo(rep, modo, alvo), []
    for i in range(0, len(x), 512):
        p.alimentar(x[i : i + 512])
        ev += j.atualizar(p.notas, p.tempo)
    p.finalizar()
    return ev + j.atualizar(p.notas, p.tempo)


@pytest.mark.skipif(not list(REP.glob("*.json")), reason="repertório local ausente")
@pytest.mark.parametrize("bpm", [70, 120])
def test_repertorio_real_nos_dois_modos(bpm):
    rep = carregar_repertorio(REP)
    for c in rep:
        livre = [e.dados["id"] for e in _rodar(rep, "livre", None, c, bpm) if e.tipo == "reconhecida"]
        assert livre == [c["id"]], (c["id"], livre)
        ap = _rodar(rep, "aprender", c["id"], c, bpm)
        assert tipos(ap)[-1] == "completa" and "divergencia" not in tipos(ap), c["id"]



def test_aprender_aceita_nota_alta_e_mostra_a_esperada():
    j = Jogo([CANCAO], "aprender", "teste")
    notas = [NotaDetectada(75, 1.0, 1.4, -45.0)]  # D5 esperado (74) tocado +55 cents: lido como D#5 -45
    ev = j.atualizar(notas, 1.0)
    assert [e.tipo for e in ev] == ["nota", "progresso"]
    assert ev[0].dados["nome"] == "D5" and ev[0].dados["cents"] == 55.0
