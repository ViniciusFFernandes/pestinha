"""
O PATCH, terceiro personagem: uma IA holográfica feita de configuração, conteúdo e do acessório
"holograma" (corpo translúcido flutuando, com brilho e fragmentos em órbita, só no desenho).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QImage  # noqa: E402

from pestinha import config  # noqa: E402
from pestinha.body.desenho_rosto import aparencia_de  # noqa: E402
from pestinha.core.protesto import DEFAULT_SIGNS, load_signs  # noqa: E402
from pestinha.paths import Paths  # noqa: E402
from tests.test_aparencia import pintar  # noqa: E402
from tests.test_jorge import frases  # noqa: E402

PATHS = Paths(root=ROOT)


def test_patch_existe_com_temperamento_paciente_e_independente():
    patch = config.load_pet(PATHS, "patch")
    assert patch["nome"] == "PATCH" and patch["reacao_notebook"] == "triste"
    t = patch["temperamento"]
    assert t["CURIOUS"] > 1 and t["LONELY->GLOOM"] < 0.5          # curioso e nada carente
    assert all(v < 1 for k, v in t.items() if k.endswith("->FRUSTRATION"))   # sem agressividade


def test_patch_tem_conteudo_proprio_completo():
    c = PATHS.conteudo("patch")
    with open(c.signs, encoding="utf-8") as f:
        secoes = set(re.findall(r"^\[(\w+)\]", f.read(), re.M))
    assert secoes == set(DEFAULT_SIGNS)
    assert all(load_signs(c.signs)[s] for s in DEFAULT_SIGNS)
    assert config.Notes(c.notes).pick() and config.Notes(c.notes_sad).pick()
    assert c.notebook == PATHS.pets / "patch" / "notebook.png"      # o terminal holográfico dele
    assert not QImage(str(c.notebook)).isNull()


def test_nada_dos_outros_pets_no_patch():
    neutras = {t for lista in DEFAULT_SIGNS.values() for t in lista}
    for outro in ("bryan", "jorge"):
        em_comum = frases("patch") & frases(outro)
        assert em_comum <= neutras, em_comum - neutras


def test_holograma_e_acessorios_desenham_em_todas_as_emocoes():
    a = aparencia_de(config.load_pet(PATHS, "patch")["aparencia"])
    nomes = [n for n, _ in a.acessorios]
    assert nomes[0] == "holograma" and {"headset", "moletom", "cafe"} <= set(nomes)
    for emocao in ("observando", "feliz", "contente", "curioso", "bravo", "triste", "dormindo", "assustado"):
        assert pintar(a, emocao) != pintar(aparencia_de(None), emocao)


def test_acessorio_desconhecido_e_ignorado():
    a = aparencia_de({"acessorios": {"holograma": "azul", "jetpack": "#ffffff"}})
    assert [n for n, _ in a.acessorios] == ["holograma"]          # cor inválida cai no padrão


def test_patch_tem_memes_proprios_em_todas_as_emocoes():
    """Gerados por ferramentas/gerar_memes_patch.py: um por emoção, no mínimo, e os de trabalho."""
    memes = PATHS.conteudo("patch").memes
    for emocao in ("feliz", "contente", "curioso", "bravo", "triste", "pensando", "sarcastico", "sonolento"):
        imagens = config.list_images(memes / emocao)
        assert imagens and not QImage(str(imagens[0])).isNull(), emocao
    assert len(config.list_images(PATHS.conteudo("patch").memes_trabalho)) >= 5
