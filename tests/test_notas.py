import pytest

from ocarina_beat.notas import cents, freq_para_midi, midi_para_freq, nome_nota, nota_mais_proxima


def test_a4_e_440():
    assert freq_para_midi(440.0) == pytest.approx(69)
    assert midi_para_freq(69) == pytest.approx(440.0)


def test_oitava_dobra_a_frequencia():
    assert midi_para_freq(81) == pytest.approx(880.0)


def test_cents_de_um_semitom():
    assert cents(midi_para_freq(70), 440.0) == pytest.approx(100.0)


def test_nota_mais_proxima_com_desvio():
    k, c = nota_mais_proxima(440.0 * 2 ** (20 / 1200))
    assert k == 69
    assert c == pytest.approx(20.0, abs=1e-6)


def test_nomes():
    assert nome_nota(69) == "A4"
    assert nome_nota(60) == "C4"
    assert nome_nota(86) == "D6"


def test_frequencia_invalida():
    with pytest.raises(ValueError):
        freq_para_midi(0)
