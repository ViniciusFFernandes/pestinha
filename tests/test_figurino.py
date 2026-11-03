"""
Acessórios de situação (mind/figurino.py) e as nuances de emoção (pensando, sarcástico, sonolento).
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pestinha import config  # noqa: E402
from pestinha.body.desenho_rosto import aparencia_de  # noqa: E402
from pestinha.core.emotion import EYE_SHAPES, refine  # noqa: E402
from pestinha.mind.figurino import Figurino, situacoes_agora  # noqa: E402
from pestinha.paths import Paths  # noqa: E402
from tests.test_aparencia import pintar  # noqa: E402

PATHS = Paths(root=ROOT)
SITUACOES = {"jogo": ["headset"], "programando": ["cafe"], "parado": ["travesseiro"], "conversa": ["balao"]}


def rodar(fig, segundos, activity="IDLE", idle=0.0, emotion="observando", inicio=0.0):
    vestindo = frozenset()
    for i in range(int(segundos * 10)):
        vestindo = fig.tick(inicio + i * 0.1, 0.1, activity, idle, emotion)
    return vestindo


def test_situacoes_vem_do_que_voce_faz_e_do_que_ele_sente():
    assert situacoes_agora("GAMING", 0, "feliz") == {"jogo"}
    assert situacoes_agora("PROGRAMMING", 0, "pensando") == {"programando"}
    assert situacoes_agora("IDLE", 400, "observando") == {"parado"}
    assert situacoes_agora("IDLE", 0, "dormindo") == {"parado"}
    assert situacoes_agora("IDLE", 0, "contente") == {"sossego"}


def test_poe_o_headset_no_jogo_e_tira_depois():
    fig = Figurino(SITUACOES, random.Random(1))
    assert "headset" in rodar(fig, 30, "GAMING")
    assert "headset" not in rodar(fig, 20, "IDLE", inicio=30)       # larga uns segundos depois


def test_cafe_e_passageiro_e_tem_pausa():
    fig = Figurino(SITUACOES, random.Random(2))
    pegou = soltou = False
    for i in range(60 * 60 * 10):                                  # uma hora programando
        v = fig.tick(i * 0.1, 0.1, "PROGRAMMING", 0.0, "pensando")
        pegou |= "cafe" in v
        soltou |= pegou and "cafe" not in v
    assert pegou and soltou                                        # não fica com o café para sempre


def test_travesseiro_quando_fica_parado():
    fig = Figurino(SITUACOES, random.Random(3))
    assert "travesseiro" not in rodar(fig, 10, "IDLE", idle=10)
    assert "travesseiro" in rodar(fig, 120, "IDLE", idle=400, inicio=10)


def test_situacao_desconhecida_e_acessorio_que_nao_existe_sao_ignorados():
    fig = Figurino({"voando": ["capa"], "jogo": ["headset"]}, random.Random(4))
    assert set(fig.situacoes) == {"jogo"}
    a = aparencia_de({"acessorios": {"headset": "#ffffff"}, "situacoes": {"jogo": ["headset", "jetpack"]}})
    assert a.situacoes == (("jogo", ("headset",)),)


def test_acessorio_de_situacao_so_aparece_vestido():
    a = aparencia_de(config.load_pet(PATHS, "patch")["aparencia"])
    assert "travesseiro" in a.de_situacao() and "moletom" not in a.de_situacao()
    assert pintar(a) != pintar_vestindo(a, {"travesseiro"})


def pintar_vestindo(aparencia, vestindo):
    from PySide6.QtGui import QImage, QPainter
    from pestinha.body.desenho_rosto import draw_face
    from pestinha.body.pet import CX, CY, WIN
    img = QImage(WIN, WIN, QImage.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.translate(CX, CY)
    draw_face(p, dict(EYE_SHAPES["observando"]), (0.0, 0.0), 1.0, "observando", aparencia=aparencia,
              vestindo=frozenset(vestindo))
    p.end()
    return img


def test_nuances_de_emocao():
    assert refine("observando", {"WATCH": 9.6, "SETTLE": 2.3}, 0.07) == "pensando"       # programando
    assert refine("observando", {"ANGRY": 9.6, "CHEER": 5.7}, 0.26) == "sarcastico"     # dispensado, achando graça
    assert refine("bravo", {"ANGRY": 13.9, "CHEER": 2.0}, 0.26) == "bravo"              # só bravo, sem graça
    assert refine("observando", {"DROWSE": 2.9}, -0.41) == "sonolento"
    assert refine("observando", {"WANDER": 1.5}, 0.18) == "observando"
    assert refine("triste", {"ANGRY": 9.0, "CHEER": 5.0}, 0.0) == "triste"
    assert {"pensando", "sarcastico", "sonolento"} <= set(EYE_SHAPES) <= set(config.EMOTION_NAMES)
