"""
Desenha pets/patch/notebook.png: o terminal holográfico do PATCH, visto por trás (como o notebook comum).

Uma tela de luz ciano translúcida, com código espelhado aparecendo do outro lado, saindo de uma base
grafite com o rostinho do PATCH. Mesmo tamanho e enquadramento de assets/comum/notebook.png,
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
    """A tela de luz: degradê translúcido, bordas acesas, linhas de varredura e código espelhado."""
    caminho = QPainterPath()
    caminho.addRoundedRect(tela, 46, 46)
    fundo = QLinearGradient(tela.topLeft(), tela.bottomRight())
    fundo.setColorAt(0.0, com_alfa(CIANO, 120))
    fundo.setColorAt(1.0, com_alfa(AZUL, 170))
    p.setPen(Qt.NoPen)
    p.setBrush(fundo)
    p.drawPath(caminho)

    p.save()
    p.setClipPath(caminho)
    p.setPen(QPen(com_alfa(BRANCO, 26), 3))
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
        p.setPen(QPen(com_alfa(cor, 120), 14, Qt.SolidLine, Qt.RoundCap))
        direita = tela.right() - 90 - recuo
        p.drawLine(QPointF(direita, y), QPointF(direita - largura, y))
        y += rng.choice((34, 34, 34, 60))
    p.restore()

    p.setBrush(Qt.NoBrush)
    for largura, alfa in ((26, 40), (12, 90), (5, 255)):  # brilho da borda, de fora para dentro
        p.setPen(QPen(com_alfa(CIANO, alfa), largura))
        p.drawPath(caminho)


def rostinho(p, centro, tamanho):
    """O logo no meio da tela: o próprio PATCH, uma telinha de contorno ciano com dois olhos."""
    x, y = centro.x(), centro.y()
    s = tamanho
    p.setPen(QPen(CIANO, 8))
    p.setBrush(com_alfa(GRAFITE, 220))
    p.drawRoundedRect(QRectF(x - s, y - s * 0.75, 2 * s, 1.5 * s), s * 0.33, s * 0.33)
    p.setPen(Qt.NoPen)
    p.setBrush(CIANO)
    for lado in (-1, 1):
        p.drawRoundedRect(QRectF(x + lado * s * 0.4 - s * 0.16, y - s * 0.3, s * 0.32, s * 0.5), 10, 10)


def desenhar(destino=DESTINO, semente=404):
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    rng = random.Random(semente)
    img = QImage(LARGURA, ALTURA, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    tela = QRectF(40, 40, 860, 680)
    feixe = QPolygonF([QPointF(170, 760), QPointF(790, 760), QPointF(860, tela.bottom() - 10),
                       QPointF(100, tela.bottom() - 10)])
    p.setPen(Qt.NoPen)
    p.setBrush(com_alfa(CIANO, 45))                     # o feixe que projeta a tela
    p.drawPolygon(feixe)
    tela_holografica(p, rng, tela)

    base = QRectF(110, 748, 940, 70)
    p.setPen(QPen(VIOLETA, 6))
    p.setBrush(GRAFITE)
    p.drawRoundedRect(base, 26, 26)
    p.setPen(QPen(com_alfa(BRANCO, 120), 4))
    p.drawLine(QPointF(base.left() + 30, base.top() + 8), QPointF(base.right() - 30, base.top() + 8))
    p.setPen(Qt.NoPen)
    p.setBrush(CIANO)
    p.drawRoundedRect(QRectF(base.left() + 200, base.top() + 30, 520, 10), 5, 5)   # emissor aceso
    p.setBrush(VERDE)
    p.drawEllipse(QPointF(base.right() - 60, base.center().y() + 6), 9, 9)          # led de ligado
    rostinho(p, QPointF(tela.center().x(), tela.center().y() + 10), 80)
    p.end()

    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(destino))
    return destino


if __name__ == "__main__":
    print(desenhar())
