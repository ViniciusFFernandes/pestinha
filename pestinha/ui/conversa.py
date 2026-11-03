"""
CONVERSA - a janelinha para conversar com o pet quando a IA está ligada.

Só mostra e manda: quem fala com a IA e guarda a memória é ia/fala.py.
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget

ESTILO = """
QWidget { background: #202631; color: #e8faff; font-family: 'Segoe UI'; font-size: 10pt; }
QTextBrowser { background: #11151c; border: 1px solid #32dceb; border-radius: 8px; padding: 6px; }
QLineEdit { background: #11151c; border: 1px solid #916bff; border-radius: 6px; padding: 6px; }
QPushButton { background: #243b72; border: 1px solid #32dceb; border-radius: 6px; padding: 6px 12px; }
QPushButton:hover { background: #2f4c91; }
QPushButton:disabled { color: #6b7894; border-color: #3a4560; }
QLabel#status { color: #8be36b; font-size: 9pt; }
"""


class JanelaConversa(QWidget):
    """Histórico, campo de texto e botão. `momento()` diz o contexto atual (emoção, atividade, hora)."""

    def __init__(self, fala, nome, momento):
        super().__init__(None, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.fala = fala
        self.nome = nome
        self.momento = momento
        self.setWindowTitle(f"Conversar com {nome}")
        self.setStyleSheet(ESTILO)
        self.resize(380, 460)

        self.historico = QTextBrowser()
        self.historico.setOpenLinks(False)
        self.campo = QLineEdit()
        self.campo.setPlaceholderText(f"Fale alguma coisa para o {nome}...")
        self.campo.returnPressed.connect(self.enviar)
        self.botao = QPushButton("Enviar")
        self.botao.clicked.connect(self.enviar)
        self.status = QLabel("")
        self.status.setObjectName("status")
        esquecer = QPushButton("Esquecer conversas")
        esquecer.clicked.connect(self.esquecer)

        linha = QHBoxLayout()
        linha.addWidget(self.campo, 1)
        linha.addWidget(self.botao)
        rodape = QHBoxLayout()
        rodape.addWidget(self.status, 1)
        rodape.addWidget(esquecer)
        layout = QVBoxLayout(self)
        layout.addWidget(self.historico, 1)
        layout.addLayout(linha)
        layout.addLayout(rodape)

        fala.respondeu.connect(self._respondeu)
        fala.falhou.connect(self._falhou)
        for m in fala.historico():
            self._mostrar("Você" if m["role"] == "user" else nome, m["content"], m["role"] == "user")

    def _mostrar(self, quem, texto, seu, cor=None):
        cor = cor or ("#916bff" if seu else "#32dceb")
        self.historico.append(f'<p><b style="color:{cor}">{html.escape(quem)}:</b> {html.escape(texto)}</p>')

    def _ocupado(self, sim):
        self.botao.setEnabled(not sim)
        self.campo.setEnabled(not sim)
        self.status.setText(f"{self.nome} está digitando..." if sim else "")
        if not sim:
            self.campo.setFocus()

    def enviar(self):
        """Manda o que está no campo."""
        texto = self.campo.text().strip()
        if not texto or not self.fala.conversar(texto, self.momento()):
            return
        self._mostrar("Você", texto, True)
        self.campo.clear()
        self._ocupado(True)

    def _respondeu(self, resposta):
        self._mostrar(self.nome, resposta, False)
        self._ocupado(False)

    def _falhou(self, motivo):
        self._mostrar(self.nome, f"(sem resposta: {motivo})", False, cor="#6b7894")
        self._ocupado(False)

    def esquecer(self):
        """Apaga a memória das conversas e limpa a janela."""
        self.fala.esquecer()
        self.historico.clear()
        self.status.setText("Memória das conversas apagada.")
