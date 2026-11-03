"""
FALA - o que o pet diz quando a IA está ligada: post-its do momento e a conversa com você.

Tudo roda numa thread separada e volta por sinal do Qt: o pet nunca trava esperando a internet.

O que vai para a IA: a personalidade do pet (pets/<pet>/personalidade.txt), o que ele lembra das
conversas, a emoção dele, a CATEGORIA do que você está fazendo (programando, jogando...) e a hora.
Nunca título de janela, site, arquivo ou o que está na tela.

Memória (memory/pets/<pet>/conversa.json):
    curto prazo  as últimas mensagens da conversa (vão inteiras em cada pedido)
    longo prazo  um resumo curto do que vale lembrar, que a própria IA atualiza de tempos em tempos
                 só com o que você disse (não inventa lembranças)
"""

import threading
import time
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from ..store import read_json, write_json
from .cliente import IAErro, conversar

CURTO_PRAZO = 20             # mensagens guardadas inteiras
RESUMIR_A_CADA = 8           # mensagens suas entre uma atualização do resumo e outra
INTERVALO_FRASE = 240        # s: no mínimo isso entre um pedido de post-it e outro
VALIDADE_FRASE = 900         # s: post-it gerado e não usado fica velho (o contexto mudou)
TAMANHO_POSTIT = 70          # caracteres

ATIVIDADES = {
    "PROGRAMMING": "programando", "DESIGNING": "projetando", "GAMING": "jogando",
    "MUSIC": "ouvindo música", "SOCIAL": "conversando num chat", "BROWSING": "navegando na internet",
    "IDLE": "no computador", "AWAY": "longe do computador",
}
DIAS = ("segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo")

REGRAS = """
Regras de estilo:
- Responda em português do Brasil, como um personagem de jogo: frases curtas e naturais.
- No máximo duas ou três frases. Sem markdown, sem listas, sem emojis em excesso.
- Não finja executar tarefas no computador e não diga que vê coisas além do que está no contexto.
- Não invente lembranças sobre o dono: use só o que está em "o que você lembra".
"""


def contexto(emocao, atividade, quando=None):
    """Uma linha com o momento: emoção dele, categoria do que você faz e a hora."""
    quando = quando or datetime.now()
    return (f"Agora: você está {emocao}; o dono está {ATIVIDADES.get(atividade, 'no computador')}; "
            f"são {quando.hour}h{quando.minute:02d} de {DIAS[quando.weekday()]}.")


def limpar_postit(texto):
    """Uma linha só, sem aspas em volta, cortada no tamanho do post-it."""
    linha = next((l.strip() for l in texto.splitlines() if l.strip()), "")
    linha = linha.strip('"“”\'').strip()
    return linha if len(linha) <= TAMANHO_POSTIT else linha[:TAMANHO_POSTIT - 1].rstrip() + "…"


class Fala(QObject):
    """As falas da IA de um pet. Sem personalidade ou sem configuração, fica indisponível."""

    respondeu = Signal(str)      # resposta da conversa
    falhou = Signal(str)         # motivo curto (sem internet, lotado...)

    def __init__(self, config, personalidade, arquivo_memoria, nome, chamar=conversar):
        super().__init__()
        self.config = config
        self.personalidade = (personalidade or "").strip()
        self.arquivo = arquivo_memoria
        self.nome = nome
        self.chamar = chamar
        self.memoria = self._ler()
        self.trava = threading.Lock()
        self.ocupada = False         # pensando numa resposta (o rosto pode mostrar o balãozinho)
        self.frase = None            # (texto, quando) do próximo post-it
        self.pedindo_frase = False
        self.ultimo_pedido = -1e9

    @property
    def disponivel(self):
        """Dá para usar: tem personalidade e chave/endereço/modelo."""
        return bool(self.personalidade) and self.config.completa

    # ---------------- memória ----------------

    def _ler(self):
        dados = read_json(self.arquivo, {}) or {}
        mensagens = [m for m in dados.get("mensagens", []) if isinstance(m, dict)
                     and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
        return {"resumo": str(dados.get("resumo", "")), "mensagens": mensagens[-CURTO_PRAZO:],
                "desde_resumo": int(dados.get("desde_resumo", 0) or 0)}

    def _gravar(self):
        try:
            write_json(self.arquivo, self.memoria, indent=1)
        except OSError:
            pass                     # sem gravar, ele só esquece; não derruba o app

    def historico(self):
        """As mensagens guardadas, para a janela de conversa mostrar ao abrir."""
        with self.trava:
            return list(self.memoria["mensagens"])

    def esquecer(self):
        """Apaga a memória das conversas (curto e longo prazo)."""
        with self.trava:
            self.memoria = {"resumo": "", "mensagens": [], "desde_resumo": 0}
            self._gravar()

    def _sistema(self, momento):
        lembra = self.memoria["resumo"] or "(nada ainda)"
        return f"{self.personalidade}\n{REGRAS}\nO que você lembra do dono:\n{lembra}\n\n{momento}"

    # ---------------- post-its ----------------

    def pedir_frase(self, momento, agora=None):
        """Pede um post-it novo em segundo plano, se não tem um guardado e já deu o intervalo."""
        agora = time.monotonic() if agora is None else agora
        if not self.disponivel or self.frase or self.pedindo_frase or agora - self.ultimo_pedido < INTERVALO_FRASE:
            return False
        self.pedindo_frase = True
        self.ultimo_pedido = agora
        mensagens = [{"role": "system", "content": self._sistema(momento)},
                     {"role": "user", "content": "Escreva UM recadinho curto (até 60 caracteres) para colar "
                                                 "na tela agora, combinando com o momento. Só o texto."}]
        threading.Thread(target=self._gerar_frase, args=(mensagens,), daemon=True).start()
        return True

    def _gerar_frase(self, mensagens):
        try:
            texto = limpar_postit(self.chamar(self.config, mensagens, max_tokens=60))
            if texto:
                self.frase = (texto, time.monotonic())
        except IAErro:
            pass                     # sem frase nova: ele usa as do recadinhos.txt
        finally:
            self.pedindo_frase = False

    def frase_pronta(self, agora=None):
        """O post-it gerado (uma vez só), ou None se não tem ou ficou velho."""
        agora = time.monotonic() if agora is None else agora
        frase, self.frase = self.frase, None
        if frase and agora - frase[1] <= VALIDADE_FRASE:
            return frase[0]
        return None

    # ---------------- conversa ----------------

    def conversar(self, texto, momento):
        """Manda sua mensagem; a resposta chega pelo sinal `respondeu` (ou `falhou`)."""
        texto = texto.strip()
        if not texto or self.ocupada:
            return False
        if not self.disponivel:
            self.falhou.emit("IA indisponível")
            return False
        self.ocupada = True
        threading.Thread(target=self._responder, args=(texto, momento), daemon=True).start()
        return True

    def _responder(self, texto, momento):
        try:
            with self.trava:
                mensagens = ([{"role": "system", "content": self._sistema(momento)}]
                             + self.memoria["mensagens"] + [{"role": "user", "content": texto}])
            resposta = self.chamar(self.config, mensagens, max_tokens=300)
        except IAErro as e:
            self.ocupada = False
            self.falhou.emit(str(e))
            return
        with self.trava:
            self.memoria["mensagens"] += [{"role": "user", "content": texto},
                                          {"role": "assistant", "content": resposta}]
            self.memoria["mensagens"] = self.memoria["mensagens"][-CURTO_PRAZO:]
            self.memoria["desde_resumo"] += 1
            resumir = self.memoria["desde_resumo"] >= RESUMIR_A_CADA
            self._gravar()
        self.ocupada = False
        self.respondeu.emit(resposta)
        if resumir:
            self._atualizar_resumo()

    def _atualizar_resumo(self):
        """Longo prazo: a IA reescreve o resumo com o que você contou (sem inventar)."""
        with self.trava:
            conversa = "\n".join(f"{'Dono' if m['role'] == 'user' else self.nome}: {m['content']}"
                                 for m in self.memoria["mensagens"])
            atual = self.memoria["resumo"] or "(vazio)"
        pedido = [{"role": "user", "content":
                   f"Resumo atual do que {self.nome} lembra do dono:\n{atual}\n\nConversa recente:\n{conversa}\n\n"
                   "Reescreva o resumo em até 8 tópicos curtos (linhas começando com '- '), só com fatos que o "
                   "DONO disse: nome, preferências, projetos, piadas recorrentes, acontecimentos marcantes. "
                   "Não invente nada. Responda só com os tópicos."}]
        try:
            resumo = self.chamar(self.config, pedido, max_tokens=300, temperatura=0.2)
        except IAErro:
            return                   # tenta de novo na próxima mensagem
        with self.trava:
            self.memoria["resumo"] = resumo.strip()[:1500]
            self.memoria["desde_resumo"] = 0
            self._gravar()
