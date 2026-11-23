import numpy as np
import pytest

from ocarina_beat.filtros import FiltroFluxo, projetar
from ocarina_beat.motor import Processador
from ocarina_beat.notas import midi_para_freq

FS = 48000


@pytest.mark.parametrize("tipo", ["iir", "fir"])
def test_passa_a_faixa_da_flauta_e_corta_fora(tipo):
    p = projetar(tipo, FS)
    g = p.resposta([60, 120, 523.25, 880, 1760, 3520, 12000])
    assert g[0] < -20 and g[1] < -20  # rede elétrica e harmônico: cortados
    assert all(abs(v) < 3 for v in g[2:6])  # Dó5..Lá7 (2º harmônico de Lá6): passa
    assert g[6] < -15  # chiado agudo: atenuado


def test_iir_e_estavel_e_fir_nao_tem_polos():
    iir, fir = projetar("iir", FS), projetar("fir", FS)
    assert iir.estavel() and len(iir.polos()) == 8 and np.all(np.abs(iir.polos()) < 1)
    assert fir.estavel() and fir.polos().size == 0


def test_atraso_do_fir_e_maior_que_o_do_iir():
    assert projetar("fir", FS).atraso_amostras() == 127
    assert projetar("iir", FS).atraso_amostras() < 127


@pytest.mark.parametrize("tipo", ["iir", "fir"])
def test_filtrar_em_blocos_e_igual_a_filtrar_tudo(tipo):
    rng = np.random.default_rng(0)
    x = rng.standard_normal(20000)
    inteiro = FiltroFluxo(projetar(tipo, FS))(x)
    f = FiltroFluxo(projetar(tipo, FS))
    blocos = np.concatenate([f(x[i : i + 700]) for i in range(0, len(x), 700)])
    assert np.allclose(inteiro, blocos)


@pytest.mark.parametrize("tipo", ["iir", "fir"])
def test_filtro_remove_zumbido_grave_e_preserva_a_nota(tipo):
    t = np.arange(FS) / FS
    nota = 0.2 * np.sin(2 * np.pi * midi_para_freq(81) * t)
    zumbido = 0.5 * np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 120 * t)
    x = np.concatenate([np.zeros(FS // 4), nota + zumbido, np.zeros(FS // 4)])
    p = Processador(FS, filtro=tipo)
    p.alimentar(x)
    assert [n.midi for n in p.finalizar()] == [81]
