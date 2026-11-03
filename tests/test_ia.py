"""
Falas com IA (pestinha/ia): cliente com reserva, memória da conversa, post-its e o que vai para fora.
Nada aqui chama a internet: a chamada é trocada por uma função falsa.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from pestinha import config  # noqa: E402
from pestinha.ia import cliente  # noqa: E402
from pestinha.ia.cliente import ConfigIA, IAErro, carregar_config, ler_env  # noqa: E402
from pestinha.ia.fala import RESUMIR_A_CADA, Fala, contexto, limpar_postit  # noqa: E402
from pestinha.paths import Paths  # noqa: E402

CONFIG = ConfigIA("chave", "https://exemplo.invalid/v1/", "principal", "reserva")
QApplication.instance() or QApplication([])


def test_le_o_env_e_o_ambiente_vale_mais(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("# comentário\nOPENAI_API_KEY='abc'\nOPENAI_MODEL=m1\nlixo\n", encoding="utf-8")
    assert ler_env(tmp_path / ".env") == {"OPENAI_API_KEY": "abc", "OPENAI_MODEL": "m1"}
    monkeypatch.setenv("OPENAI_MODEL", "m2")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    c = carregar_config(tmp_path)
    assert (c.chave, c.modelo, c.completa) == ("abc", "m2", False)        # sem endereço: incompleta


def test_lotado_tenta_de_novo_e_vai_para_a_reserva(monkeypatch):
    chamados = []

    def falso(config, modelo, *_):
        chamados.append(modelo)
        if modelo == "principal":
            raise cliente._Passageiro("HTTP 503")
        return "oi"
    monkeypatch.setattr(cliente, "_chamar", falso)
    assert cliente.conversar(CONFIG, [], esperar=lambda s: None) == "oi"
    assert chamados == ["principal", "principal", "reserva"]


def test_demorou_demais_pula_direto_para_a_reserva(monkeypatch):
    chamados = []

    def falso(config, modelo, *_):
        chamados.append(modelo)
        if modelo == "principal":
            raise cliente._Passageiro("demorou", repetir=False)
        return "oi"
    monkeypatch.setattr(cliente, "_chamar", falso)
    assert cliente.conversar(CONFIG, [], esperar=lambda s: None) == "oi"
    assert chamados == ["principal", "reserva"]


def test_sem_reserva_e_tudo_lotado_vira_erro(monkeypatch):
    def falso(*_):
        raise cliente._Passageiro("HTTP 429")
    monkeypatch.setattr(cliente, "_chamar", falso)
    with pytest.raises(IAErro):
        cliente.conversar(ConfigIA("c", "e", "m"), [], esperar=lambda s: None)
    with pytest.raises(IAErro):
        cliente.conversar(ConfigIA(), [])                                   # sem configuração


def fala_falsa(tmp_path, respostas=None, personalidade="Você é um teste."):
    pedidos = []

    def chamar(config, mensagens, **_):
        pedidos.append(mensagens)
        resposta = (respostas or {}).get(len(pedidos), "resposta")
        if isinstance(resposta, Exception):
            raise resposta
        return resposta
    fala = Fala(CONFIG, personalidade, tmp_path / "conversa.json", "PATCH", chamar=chamar)
    return fala, pedidos


def test_conversa_guarda_memoria_e_manda_o_contexto(tmp_path):
    fala, pedidos = fala_falsa(tmp_path)
    recebidas = []
    fala.respondeu.connect(recebidas.append)
    fala._responder("oi", contexto("feliz", "PROGRAMMING"))
    assert recebidas == ["resposta"]
    sistema = pedidos[0][0]["content"]
    assert "Você é um teste." in sistema and "programando" in sistema and "feliz" in sistema
    assert fala.historico() == [{"role": "user", "content": "oi"}, {"role": "assistant", "content": "resposta"}]
    de_novo = Fala(CONFIG, "x", tmp_path / "conversa.json", "PATCH")         # lembra depois de reabrir
    assert len(de_novo.historico()) == 2


def test_falha_avisa_e_nao_guarda(tmp_path):
    fala, _ = fala_falsa(tmp_path, {1: IAErro("sem conexão")})
    motivos = []
    fala.falhou.connect(motivos.append)
    fala._responder("oi", "agora")
    assert motivos == ["sem conexão"] and fala.historico() == [] and not fala.ocupada


def test_resumo_de_longo_prazo_so_de_tempos_em_tempos(tmp_path):
    respostas = {RESUMIR_A_CADA + 1: "- gosta de PHP"}           # a chamada logo depois da 8ª mensagem
    fala, pedidos = fala_falsa(tmp_path, respostas)
    for i in range(RESUMIR_A_CADA):
        fala._responder(f"mensagem {i}", "agora")
    assert len(pedidos) == RESUMIR_A_CADA + 1                             # +1: o pedido de resumo
    assert "Não invente" in pedidos[-1][0]["content"]
    assert fala.memoria["resumo"] == "- gosta de PHP" and fala.memoria["desde_resumo"] == 0
    fala._responder("e agora?", "agora")
    assert "- gosta de PHP" in pedidos[-1][0]["content"]                  # o resumo vai no próximo pedido


def test_post_it_tem_intervalo_e_validade(tmp_path):
    fala, _ = fala_falsa(tmp_path, {1: '"Esse JOIN me assusta."\nsegunda linha'})
    fala._gerar_frase([])
    assert fala.frase_pronta() == "Esse JOIN me assusta."
    assert fala.frase_pronta() is None                                    # uma vez só
    fala.frase = ("velha", 0.0)
    assert fala.frase_pronta(agora=10_000) is None
    fala.ultimo_pedido = 100.0
    assert not fala.pedir_frase("agora", agora=150.0)                     # ainda no intervalo
    assert limpar_postit("x" * 200).endswith("…") and len(limpar_postit("x" * 200)) == 70


def test_sem_personalidade_ou_sem_chave_fica_indisponivel(tmp_path):
    assert not Fala(CONFIG, "", tmp_path / "c.json", "Bryan").disponivel
    assert not Fala(ConfigIA(), "x", tmp_path / "c.json", "PATCH").disponivel
    paths = Paths(root=ROOT)
    assert paths.conteudo("patch").personalidade.exists()
    assert not paths.conteudo("bryan").personalidade.exists()            # Bryan e Jorge seguem sem IA


def test_contexto_so_tem_categoria_e_hora():
    texto = contexto("sarcástico", "BROWSING")
    assert "navegando" in texto and "sarcástico" in texto
    assert contexto("feliz", "QUALQUER").count("no computador") == 1


def test_permissao_vem_desligada():
    assert config.DEFAULT_PERMISSIONS["ia"] is False
    chaves = {k for _grupo, itens in config.PERMISSION_GROUPS for k, *_ in itens}
    assert "ia" in chaves
