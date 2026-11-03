"""
Desenha pets/patch/notebook.png: o terminal holográfico do PATCH, visto por trás (como o notebook comum).

Uma tela de vidro escuro com bordas de luz ciano e o código espelhado aparecendo do outro lado,
projetada por uma base grafite. O vidro é quase opaco de propósito: sentado, o pet fica com a parte
de baixo escondida atrás da tela, e um vidro transparente mostraria a área de trabalho no lugar dele.
A tela fica centralizada na imagem, porque o pet senta no meio dela. Mesmo tamanho e enquadramento de assets/comum/notebook.png,
para cair no mesmo lugar da mesa. Desenho feito por código (sem imagem de terceiros).
Rode de novo para refazer o arquivo.
"""
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
)

LARGURA, ALTURA = 1154, 850
DESTINO = Path(__file__).resolve().parent.parent / "pets" / "patch" / "notebook.png"

CIANO = QColor("#32dceb")
VERDE = QColor("#8be36b")
VIOLETA = QColor("#916bff")
AZUL = QColor("#243b72")
BRANCO = QColor("#e8faff")
GRAFITE = QColor("#202631")


def com_alfa(cor, alfa):
    c = QColor(cor)
    c.setAlpha(alfa)
    return c


def tela_holografica(p, rng, tela):
    """A tela: vidro escuro quase opaco, bordas acesas, linhas de varredura e código espelhado."""
    caminho = QPainterPath()
    caminho.addRoundedRect(tela, 46, 46)
    fundo = QLinearGradient(tela.topLeft(), tela.bottomRight())
    fundo.setColorAt(0.0, com_alfa(QColor("#1d3a66"), 245))
    fundo.setColorAt(1.0, com_alfa(GRAFITE, 250))
    p.setPen(Qt.NoPen)
    p.setBrush(fundo)
    p.drawPath(caminho)

    p.save()
    p.setClipPath(caminho)
    p.setPen(QPen(com_alfa(CIANO, 22), 3))
    y = tela.top() + 6
    while y < tela.bottom():                            # linhas de varredura do holograma
        p.drawLine(QPointF(tela.left(), y), QPointF(tela.right(), y))
        y += 14
    # código visto do outro lado da tela: blocos de linhas, indentados, da direita para a esquerda
    y = tela.top() + 80
    while y < tela.bottom() - 70:
        recuo = rng.choice((0, 0, 50, 50, 100))
        largura = rng.uniform(120, 460)
        cor = rng.choice((VERDE, CIANO, VIOLETA, BRANCO))
        p.setPen(QPen(com_alfa(cor, 150), 14, Qt.SolidLine, Qt.RoundCap))
        direita = tela.right() - 90 - recuo
        p.drawLine(QPointF(direita, y), QPointF(direita - largura, y))
        y += rng.choice((34, 34, 34, 60))
    p.restore()

    p.setBrush(Qt.NoBrush)
    for largura, alfa in ((26, 40), (12, 90), (5, 255)):  # brilho da borda, de fora para dentro
        p.setPen(QPen(com_alfa(CIANO, alfa), largura))
        p.drawPath(caminho)


def desenhar(destino=DESTINO, semente=404):
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    rng = random.Random(semente)
    img = QImage(LARGURA, ALTURA, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    tela = QRectF((LARGURA - 900) / 2, 30, 900, 690)
    feixe = QPolygonF([QPointF(tela.left() + 130, 760), QPointF(tela.right() - 130, 760),
                       QPointF(tela.right() - 40, tela.bottom() - 10), QPointF(tela.left() + 40, tela.bottom() - 10)])
    p.setPen(Qt.NoPen)
    p.setBrush(com_alfa(CIANO, 45))                     # o feixe que projeta a tela
    p.drawPolygon(feixe)
    tela_holografica(p, rng, tela)

    base = QRectF((LARGURA - 940) / 2, 748, 940, 70)
    p.setPen(QPen(VIOLETA, 6))
    p.setBrush(GRAFITE)
    p.drawRoundedRect(base, 26, 26)
    p.setPen(QPen(com_alfa(BRANCO, 120), 4))
    p.drawLine(QPointF(base.left() + 30, base.top() + 8), QPointF(base.right() - 30, base.top() + 8))
    p.setPen(Qt.NoPen)
    p.setBrush(CIANO)
    p.drawRoundedRect(QRectF(base.center().x() - 260, base.top() + 30, 520, 10), 5, 5)   # emissor aceso
    p.setBrush(VERDE)
    p.drawEllipse(QPointF(base.right() - 60, base.center().y() + 6), 9, 9)          # led de ligado
    p.end()

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(destino))
    return destino


if __name__ == "__main__":
    print(desenhar())
