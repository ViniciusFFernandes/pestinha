"""
CLIENTE - uma chamada de chat para qualquer serviço compatível com a API da OpenAI.

Funciona com o Gemini (endereço /v1beta/openai/), a própria OpenAI, Groq ou o Ollama local, só
mudando as variáveis. Elas vêm do ambiente ou do arquivo .env na raiz do projeto (que não
vai para o git):

    OPENAI_API_KEY=...
    OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    OPENAI_MODEL=gemini-3.8-flash
    OPENAI_MODEL_RESERVA=gemini-flash-lite-latest     (opcional: usado quando o principal está lotado)

Só biblioteca padrão (urllib): nenhuma dependência nova. A chamada bloqueia; quem usa roda em
segundo plano (ia/fala.py).
"""

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

TIMEOUT = 20                 # s por chamada (estourou: vai para o reserva)
CHAVES = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "OPENAI_MODEL_RESERVA")
PASSAGEIROS = (429, 500, 502, 503)   # lotado ou limite por minuto: vale tentar de novo / ir para a reserva
ESPERA = 1.5                 # s antes de tentar o mesmo modelo de novo


class IAErro(Exception):
    """A IA não respondeu (sem chave, sem internet, limite do plano, resposta estranha)."""


@dataclass(frozen=True)
class ConfigIA:
    chave: str = ""
    endereco: str = ""
    modelo: str = ""
    reserva: str = ""

    @property
    def completa(self):
        """Diz se dá para chamar: chave, endereço e modelo preenchidos."""
        return bool(self.chave and self.endereco and self.modelo)


def ler_env(caminho):
    """Lê um .env simples (CHAVE=valor por linha, # é comentário). Arquivo ausente vira {}."""
    valores = {}
    try:
        linhas = caminho.read_text(encoding="utf-8").splitlines()
    except OSError:
        return valores
    for linha in linhas:
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        valores[chave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def carregar_config(raiz):
    """Configuração da IA: variáveis de ambiente valem mais que o .env da raiz."""
    arquivo = ler_env(raiz / ".env")
    pega = {k: os.environ.get(k) or arquivo.get(k, "") for k in CHAVES}
    return ConfigIA(pega["OPENAI_API_KEY"], pega["OPENAI_BASE_URL"], pega["OPENAI_MODEL"], pega["OPENAI_MODEL_RESERVA"])


class _Passageiro(IAErro):
    """Erro que passa sozinho (modelo lotado, limite por minuto, lento demais)."""

    def __init__(self, motivo, repetir=True):
        super().__init__(motivo)
        self.repetir = repetir       # False: nem tenta o mesmo modelo de novo (demorou demais)


def conversar(config, mensagens, max_tokens=200, temperatura=0.9, esperar=time.sleep):
    """
    Manda a conversa (lista de {"role", "content"}) e devolve o texto da resposta.
    Modelo lotado: tenta de novo uma vez e depois vai para o reserva, se houver.
    Qualquer falha vira IAErro, com uma mensagem curta (nunca a chave).
    """
    if not config.completa:
        raise IAErro("IA sem configuração (.env)")
    tentativas = [config.modelo, config.modelo] + ([config.reserva] if config.reserva else [])
    pular = None
    for i, modelo in enumerate(tentativas):
        if modelo == pular:
            continue
        try:
            return _chamar(config, modelo, mensagens, max_tokens, temperatura)
        except _Passageiro as e:
            restantes = [m for m in tentativas[i + 1:] if e.repetir or m != modelo]
            if not restantes:
                raise IAErro("modelo lotado, tente daqui a pouco") from None
            if not e.repetir:
                pular = modelo
            elif restantes[0] == modelo:
                esperar(ESPERA)


def _chamar(config, modelo, mensagens, max_tokens, temperatura):
    """Uma chamada a um modelo. Erro passageiro sai como _Passageiro."""
    corpo = json.dumps({"model": modelo, "messages": mensagens, "max_tokens": max_tokens,
                        "temperature": temperatura}).encode("utf-8")
    pedido = urllib.request.Request(
        config.endereco.rstrip("/") + "/chat/completions", data=corpo, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.chave}"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in PASSAGEIROS:
            raise _Passageiro(f"HTTP {e.code}") from None
        raise IAErro(f"HTTP {e.code}") from None
    except TimeoutError:
        raise _Passageiro("demorou demais", repetir=False) from None
    except (urllib.error.URLError, OSError) as e:
        if isinstance(getattr(e, "reason", None), TimeoutError):
            raise _Passageiro("demorou demais", repetir=False) from None
        raise IAErro(f"sem conexão: {getattr(e, 'reason', e)}") from None
    except ValueError:
        raise IAErro("resposta que não é JSON") from None
    try:
        texto = dados["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise IAErro("resposta sem texto") from None
    if not isinstance(texto, str) or not texto.strip():
        raise IAErro("resposta vazia")
    return texto.strip()
