import mido
import pytest

from ocarina_beat.repertorio import ler_notas, oitavas_para_caber, para_cancao


def midi_de_teste(tmp_path, notas, ppq=48):
    """notas: lista de (midi, inicio_em_batidas, duracao_em_batidas) no canal 3."""
    eventos = []
    for n, ini, dur in notas:
        eventos.append((round(ini * ppq), "note_on", n))
        eventos.append((round((ini + dur) * ppq), "note_off", n))
    trilha, t = mido.MidiTrack(), 0
    for tick, tipo, n in sorted(eventos):
        trilha.append(mido.Message(tipo, note=n, velocity=64, channel=3, time=tick - t))
        t = tick
    mid = mido.MidiFile(ticks_per_beat=ppq)
    mid.tracks.append(trilha)
    caminho = tmp_path / "t.mid"
    mid.save(caminho)
    return caminho


def test_duracao_e_o_intervalo_entre_inicios(tmp_path):
    # nota curta com pausa depois: o ritmo vem do início da próxima, não da duração
    c = midi_de_teste(tmp_path, [(74, 0, 0.25), (76, 1, 0.5), (79, 2, 2)])
    cancao = para_cancao(ler_notas(c, 0, 3), "x", "X", "t.mid")
    assert [n["beats"] for n in cancao["notes"]] == [1.0, 1.0, 2.0]


def test_transpoe_para_caber_na_faixa(tmp_path):
    c = midi_de_teste(tmp_path, [(62, 0, 1), (64, 1, 1), (60, 2, 1)])  # D4 E4 C4
    notas = ler_notas(c, 0, 3)
    assert oitavas_para_caber(notas) == 1
    assert [n["midi"] for n in para_cancao(notas, "x", "X", "t")["notes"]] == [74, 76, 72]


def test_descarta_notas_espurias(tmp_path):
    c = midi_de_teste(tmp_path, [(62, 0, 0.02), (64, 1, 1)])
    assert len(ler_notas(c, 0, 3)) == 1


def test_melodia_fora_da_faixa(tmp_path):
    c = midi_de_teste(tmp_path, [(40, 0, 1), (100, 1, 1)])
    with pytest.raises(ValueError):
        oitavas_para_caber(ler_notas(c, 0, 3))


def test_reconhecer_primeiras_mantem_a_melodia_completa(tmp_path):
    c = midi_de_teste(tmp_path, [(74, 0, 1), (76, 1, 1), (79, 2, 1), (76, 3, 1)])
    cancao = para_cancao(ler_notas(c, 0, 3), "x", "X", "t", reconhecer_primeiras=2)
    assert cancao["reconhecer_primeiras"] == 2
    assert len(cancao["notes"]) == 4


def test_sem_reconhecer_primeiras_usa_a_cancao_inteira(tmp_path):
    c = midi_de_teste(tmp_path, [(74, 0, 1), (76, 1, 1), (79, 2, 1)])
    assert para_cancao(ler_notas(c, 0, 3), "x", "X", "t")["reconhecer_primeiras"] == 3
