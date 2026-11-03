"""
DESENHO DO ROSTO - só o que se desenha do pet: moldura, olhos, brilho, acessórios e os Zzz.

Não tem estado nem decisão: recebe a forma dos olhos, a direção do olhar e a aparência do pet
(cores e acessórios, de pets/<pet>.json) e pinta. Os acessórios são camadas em volta do rosto:
não mudam os olhos nem as expressões. O "holograma" é o único que mexe no corpo: ele flutua,
fica translúcido e ganha brilho e fragmentos em órbita (só no desenho; a física não muda).
"""

import math
import re
import time
from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainterPath, QPen, QPolygonF

from ..ajustes import ZZZ_PERIODO as ZZZ_PERIOD, ZZZ_QUANTIDADE as ZZZ_COUNT

BODY_W, BODY_H = 120, 90
FRAME = QColor("#63e56f")
SHELL = QColor("#101512")
SCREEN = QColor("#171e19")
EYE = QColor("#3ee877")
SHINE = QColor("#c8ffd8")

ACESSORIOS = ("holograma", "travesseiro", "oculos", "gravata", "moletom", "circuitos", "headset", "cursor", "cafe",
              "notas", "balao")
COR_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
COR_PADRAO_ACESSORIO = {"oculos": "#e8e8e8", "gravata": "#b3261e", "holograma": "#32dceb", "moletom": "#202631",
                        "circuitos": "#916bff", "headset": "#916bff", "cursor": "#8be36b", "cafe": "#e8faff",
                        "travesseiro": "#916bff", "notas": "#8be36b", "balao": "#e8faff"}


@dataclass(frozen=True)
class Aparencia:
    """Cores do corpo e acessórios de um pet. O padrão é o visual original (o do pet)."""
    moldura: QColor = field(default_factory=lambda: QColor(FRAME))
    casca: QColor = field(default_factory=lambda: QColor(SHELL))
    tela: QColor = field(default_factory=lambda: QColor(SCREEN))
    olho: QColor = field(default_factory=lambda: QColor(EYE))
    brilho: QColor = field(default_factory=lambda: QColor(SHINE))
    acessorios: tuple = ()             # ((nome, QColor), ...) na ordem em que são desenhados
    situacoes: tuple = ()              # ((situação, (acessório, ...)), ...): só aparecem quando ele pega (mind/figurino.py)

    def de_situacao(self):
        """Acessórios que dependem da situação (os outros ficam sempre no corpo)."""
        return {nome for _s, nomes in self.situacoes for nome in nomes}


CAMPOS_DE_COR = ("moldura", "casca", "tela", "olho", "brilho")


def aparencia_de(dados):
    """
    Monta a Aparencia a partir do "aparencia" do pet.json. Cor fora do formato #rrggbb e
    acessório desconhecido são ignorados (ficam com o padrão), como os outros campos do pet.
    Em "situacoes", só valem acessórios que também estão em "acessorios".
    """
    if not isinstance(dados, dict):
        return Aparencia()
    cores = {k: QColor(dados[k]) for k in CAMPOS_DE_COR
             if isinstance(dados.get(k), str) and COR_HEX.match(dados[k])}
    pedidos = dados.get("acessorios")
    acessorios = []
    if isinstance(pedidos, dict):
        for nome in ACESSORIOS:                         # ordem fixa: a gravata não cobre os óculos
            if nome in pedidos:
                cor = pedidos[nome]
                cor = cor if isinstance(cor, str) and COR_HEX.match(cor) else COR_PADRAO_ACESSORIO[nome]
                acessorios.append((nome, QColor(cor)))
    tem = {nome for nome, _ in acessorios}
    situacoes = []
    if isinstance(dados.get("situacoes"), dict):
        for situacao, nomes in dados["situacoes"].items():
            if isinstance(nomes, list):
                situacoes.append((situacao, tuple(n for n in nomes if n in tem)))
    return Aparencia(**cores, acessorios=tuple(acessorios), situacoes=tuple(situacoes))


PADRAO = Aparencia()


def lerp_shape(current, target, k):
    """Interpola duas formas de olho: `k` entre 0 (atual) e 1 (alvo), para a transição ser suave."""
    return {key: current[key] + (target[key] - current[key]) * k for key in target}


def draw_face(p, shape, gaze=(0.0, 0.0), blink=1.0, emotion="observando", carinho=False, aparencia=PADRAO,
              vestindo=frozenset()):
    """
    Desenha moldura + tela + olhos (+ acessórios) com centro na origem do painter. Acessório de
    situação só aparece se estiver em `vestindo` (o que o figurino decidiu agora).
    """
    a = aparencia
    agora = time.monotonic()
    de_situacao = a.de_situacao()
    acessorios = [(n, c) for n, c in a.acessorios if n not in de_situacao or n in vestindo]
    holo = dict(a.acessorios).get("holograma")
    casca, tela = a.casca, a.tela
    if holo:
        # holograma: o corpo flutua (desenhado deslocado e inclinado) sobre um brilho parado no chão
        _holo_projecao(p, holo, agora)
        p.save()
        dy, inclina = _holo_flutua(agora, emotion)
        p.translate(0, dy)
        p.rotate(inclina)
        _holo_aura(p, holo, agora)
        _holo_fragmentos(p, holo, agora, a, frente=False)
        casca, tela = QColor(casca), QColor(tela)
        casca.setAlpha(200)                             # translúcido, mas a tela segura o contraste dos olhos
        tela.setAlpha(235)
    for nome, cor in acessorios:
        if nome == "headset":                          # o arco passa por trás da cabeça
            _headset_arco(p, cor)
        elif nome == "travesseiro":                    # atrás do corpo: ele se encosta
            _travesseiro(p, cor)
    p.setPen(QPen(a.moldura, 5))
    p.setBrush(casca)
    p.drawRoundedRect(QRectF(-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H), 20, 20)
    p.setPen(Qt.NoPen)
    p.setBrush(tela)
    p.drawRoundedRect(QRectF(-BODY_W / 2 + 11, -BODY_H / 2 + 11, BODY_W - 22, BODY_H - 22), 12, 12)
    if holo:
        _holo_varredura(p, holo, agora)
        if "reflexo" in vestindo:                      # sentado no terminal: a luz da tela bate no rosto
            _holo_reflexo(p, holo, agora)
    for nome, cor in acessorios:
        if nome == "gravata":                          # por cima da tela, sempre dentro do contorno do corpo
            _gravata(p, cor)
        elif nome == "moletom":
            _moletom(p, cor, a)
        elif nome == "circuitos":
            _circuitos(p, cor)

    if carinho:
        # carinho: olhinhos fechados de felicidade, em arco para cima (^ ^)
        p.setPen(QPen(a.olho, 5, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        for side in (-1, 1):
            cx, cy = side * 24, shape["dy"]
            p.drawArc(QRectF(cx - 15, cy - 8, 30, 22), 0, 180 * 16)
        p.setPen(Qt.NoPen)
    else:
        _olhos(p, shape, gaze, blink, emotion, a, olhando_tela="reflexo" in vestindo)
        if emotion == "pensando":
            _reticencias(p, a, agora)
    for nome, cor in acessorios:
        if nome == "oculos":
            _oculos(p, cor)
        elif nome == "headset":
            _headset_conchas(p, cor, a)
        elif nome == "cursor":
            _cursor(p, cor, agora)
        elif nome == "cafe":
            _cafe(p, cor, agora)
        elif nome == "notas":
            _notas(p, cor, agora)
        elif nome == "balao":
            _balao(p, cor, agora)
    if holo:
        _holo_fragmentos(p, holo, agora, a, frente=True)
        p.restore()


def _olhos(p, shape, gaze, blink, emotion, a, olhando_tela=False):
    """Desenha os dois olhos: forma, piscada, brilho e direção do olhar."""
    perdido = emotion == "pensando" and not olhando_tela        # pensando: olhar perdido, para cima
    gx, gy = (0.9, -1.0) if perdido else gaze                  # (no notebook, olha para a tela)
    for side in (-1, 1):
        w = shape["w"]
        h = shape["h"] * blink
        if emotion == "curioso" and side == 1:
            h *= 1.15
        elif emotion == "sarcastico":                  # um olho apertado e o outro erguido: "sei..."
            h *= 0.5 if side == -1 else 1.12
        h = max(h, 3.0)
        cx = side * 24 + gx * 4
        cy = shape["dy"] + gy * 3 + (5 if emotion == "sarcastico" and side == -1 else 0)
        top = cy - h / 2

        eye = QPainterPath()
        eye.addRoundedRect(QRectF(cx - w / 2, top, w, h), min(w, h) * 0.38, min(w, h) * 0.38)

        if blink > 0.5:
            outer_x = cx + side * w / 2
            inner_x = cx - side * w / 2
            lid = QPainterPath()
            lid.addPolygon(QPolygonF([
                QPointF(outer_x + side * 4, top - 40),
                QPointF(inner_x - side * 4, top - 40),
                QPointF(inner_x - side * 4, top + shape["inner"] * h),
                QPointF(outer_x + side * 4, top + shape["outer"] * h),
            ]))
            eye = eye.subtracted(lid)
            if shape["smile"] > 0.02:
                cut = QPainterPath()
                ch = h * shape["smile"] * 1.6
                cut.addEllipse(QRectF(cx - w * 0.75, top + h - ch * 0.45, w * 1.5, ch))
                eye = eye.subtracted(cut)

        p.setBrush(a.olho)
        p.drawPath(eye)

        if blink > 0.5 and h >= 8:                 # olho fechado não tem brilho
            p.save()
            p.setClipPath(eye)
            p.setBrush(a.brilho)
            sx = cx - w * 0.18 + gx * 3
            sy = top + h * (0.24 + max(shape["inner"], shape["outer"]) * 0.6) + gy * 2
            p.drawEllipse(QPointF(sx, sy), 3.6, 3.6)
            p.restore()



def _reticencias(p, a, agora):
    """Três pontinhos acendendo em sequência embaixo dos olhos: "processando..." """
    p.save()
    p.setPen(Qt.NoPen)
    for i in range(3):
        cor = QColor(a.olho)
        cor.setAlpha(255 if int(agora * 3) % 4 > i else 70)
        p.setBrush(cor)
        p.drawEllipse(QPointF(-10 + i * 10, BODY_H / 2 - 22), 2.8, 2.8)
    p.restore()


def _oculos(p, cor):
    """Armação por cima dos olhos: aro grosso em cima, fino embaixo, e a ponte no meio."""
    p.save()
    p.setBrush(Qt.NoBrush)
    for side in (-1, 1):
        lente = QRectF(side * 24 - 21, -25, 42, 52)
        vidro = QColor(cor)
        vidro.setAlpha(22)                              # um reflexo leve: o olho continua aparecendo
        p.setPen(Qt.NoPen)
        p.setBrush(vidro)
        p.drawRoundedRect(lente, 10, 10)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(cor, 2))
        p.drawRoundedRect(lente, 10, 10)
        p.setPen(QPen(cor, 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(lente.left() + 4, lente.top()), QPointF(lente.right() - 4, lente.top()))
    p.setPen(QPen(cor, 3, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(-3, -18), QPointF(3, -18))       # ponte
    p.restore()


def _gravata(p, cor):
    """
    Gravata na frente do peito, dentro do contorno do corpo. Termina antes da borda de baixo para
    não cair na barra de tarefas quando ele anda sobre ela.
    """
    p.save()
    topo = BODY_H / 2 - 24                              # nó logo abaixo da tela, cola no contorno
    escura = cor.darker(140)
    p.setPen(QPen(escura, 1.2))
    p.setBrush(cor)
    p.drawPolygon(QPolygonF([QPointF(-4, topo), QPointF(4, topo), QPointF(3.5, topo + 6),
                             QPointF(-3.5, topo + 6)]))          # nó
    p.drawPolygon(QPolygonF([QPointF(-3, topo + 5), QPointF(3, topo + 5), QPointF(5.5, topo + 17),
                             QPointF(0, topo + 21), QPointF(-5.5, topo + 17)]))   # ponta
    p.setPen(QPen(escura, 1.5))
    p.drawLine(QPointF(-4, topo + 10), QPointF(4, topo + 8))                   # listra
    p.restore()


def _holo_flutua(agora, emotion):
    """
    Flutuação do holograma: (deslocamento vertical, inclinação em graus). Sobe e desce devagar e
    balança de leve; feliz flutua mais alto e mais rápido, dormindo quase pousa, curioso inclina.
    """
    if emotion == "dormindo":
        return -2 + 1.5 * math.sin(agora * 0.8), 0.0
    altura, ritmo = (5.0, 3.0) if emotion == "feliz" else (3.0, 1.7)
    inclina = 8.0 if emotion == "curioso" else 0.0
    return -6 + altura * math.sin(agora * ritmo), inclina + 2.5 * math.sin(agora * 0.9)


def _holo_projecao(p, cor, agora):
    """O brilho no chão embaixo dele: o "projetor" do holograma. Fica parado enquanto o corpo flutua."""
    luz = QColor(cor)
    luz.setAlpha(int(55 + 25 * math.sin(agora * 2.0)))
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(luz)
    p.drawEllipse(QPointF(0, BODY_H / 2 + 1), 40, 4)
    p.restore()


def _holo_aura(p, cor, agora):
    """Contorno luminoso pulsando em volta do corpo (duas passadas largas e transparentes)."""
    pulso = 0.5 + 0.5 * math.sin(agora * 2.0)
    p.save()
    p.setBrush(Qt.NoBrush)
    for largura, alfa in ((16, 18 + 22 * pulso), (9, 40 + 40 * pulso)):
        luz = QColor(cor)
        luz.setAlpha(int(alfa))
        p.setPen(QPen(luz, largura))
        p.drawRoundedRect(QRectF(-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H), 20, 20)
    p.restore()


FRAGMENTOS = 12                                         # quadradinhos orbitando (limite de partículas)


def _holo_fragmentos(p, cor, agora, a, frente):
    """
    Fragmentos girando num anel inclinado em volta do corpo, sem cruzar a frente do rosto. Os de trás são desenhados antes do
    corpo (`frente=False`) e os da frente depois, para parecer que passam por trás dele.
    """
    p.save()
    p.setPen(Qt.NoPen)
    for i in range(FRAGMENTOS):
        ang = agora * (0.55 + 0.05 * (i % 3)) + i * math.tau / FRAGMENTOS
        profundidade = math.sin(ang)                    # > 0: na frente do corpo
        if (profundidade > 0) != frente:
            continue
        x = math.cos(ang) * (74 + 6 * (i % 2))
        y = -2 + profundidade * 50 + 4 * math.sin(agora * 0.7 + i)   # anel inclinado: a frente passa por baixo do rosto
        lado = 2.5 + 1.5 * (i % 3) + profundidade
        luz = QColor(cor if i % 3 else a.brilho)
        luz.setAlpha(int(150 + 90 * profundidade) if frente else int(70 + 50 * (1 + profundidade)))
        p.save()
        p.translate(x, y)
        p.rotate(45 + agora * 40 + i * 30)
        p.setBrush(luz)
        p.drawRect(QRectF(-lado / 2, -lado / 2, lado, lado))
        p.restore()
    p.restore()


def _holo_reflexo(p, cor, agora):
    """Luz da tela do terminal subindo pela tela do rosto, de baixo para cima, piscando de leve."""
    tela = QRectF(-BODY_W / 2 + 11, -BODY_H / 2 + 11, BODY_W - 22, BODY_H - 22)
    luz = QLinearGradient(QPointF(0, tela.bottom()), QPointF(0, tela.top()))
    forte = QColor(cor)
    forte.setAlpha(int(80 + 15 * math.sin(agora * 3.1)))
    fraca = QColor(cor)
    fraca.setAlpha(0)
    luz.setColorAt(0.0, forte)
    luz.setColorAt(0.7, fraca)
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(luz)
    p.drawRoundedRect(tela, 12, 12)
    p.restore()


def _holo_varredura(p, cor, agora):
    """
    Linhas de varredura bem fracas na tela, uma faixa de luz descendo devagar e, raramente, uma
    interferência rápida (um risco deslocado por um instante). Não atrapalha a leitura dos olhos.
    """
    tela = QRectF(-BODY_W / 2 + 11, -BODY_H / 2 + 11, BODY_W - 22, BODY_H - 22)
    recorte = QPainterPath()
    recorte.addRoundedRect(tela, 12, 12)
    p.save()
    p.setClipPath(recorte)
    fraca = QColor(cor)
    fraca.setAlpha(16)
    p.setPen(QPen(fraca, 1))
    y = tela.top() + 2
    while y < tela.bottom():
        p.drawLine(QPointF(tela.left(), y), QPointF(tela.right(), y))
        y += 5
    faixa = QColor(cor)
    faixa.setAlpha(34)
    p.setPen(Qt.NoPen)
    p.setBrush(faixa)
    p.drawRect(QRectF(tela.left(), tela.top() - 8 + (agora * 22) % (tela.height() + 16), tela.width(), 6))
    if (agora % 9.0) < 0.12:                            # interferência: ~1 vez a cada 9 s, por um instante
        risco = QColor(cor)
        risco.setAlpha(120)
        p.setBrush(risco)
        p.drawRect(QRectF(tela.left() + 8, tela.top() + (agora * 997) % tela.height(), tela.width() * 0.6, 2))
    p.restore()


def _moletom(p, cor, a):
    """Gola de moletom hacker na base do corpo, com cordões prateados e um circuito aceso."""
    p.save()
    gola = QPainterPath()
    gola.addRoundedRect(QRectF(-BODY_W / 2, BODY_H / 2 - 14, BODY_W, 14), 6, 6)
    corpo = QPainterPath()
    corpo.addRoundedRect(QRectF(-BODY_W / 2, -BODY_H / 2, BODY_W, BODY_H), 20, 20)
    p.setPen(Qt.NoPen)
    p.setBrush(cor)
    p.drawPath(gola.intersected(corpo))
    p.setPen(QPen(a.moldura, 2, Qt.SolidLine, Qt.RoundCap))
    for side in (-1, 1):                                # cordões do capuz
        p.drawLine(QPointF(side * 10, BODY_H / 2 - 13), QPointF(side * 12, BODY_H / 2 - 4))
    luz = QColor(a.olho)
    luz.setAlpha(190)
    p.setPen(QPen(luz, 1.5))
    p.drawPolyline(QPolygonF([QPointF(-46, BODY_H / 2 - 6), QPointF(-34, BODY_H / 2 - 6),
                              QPointF(-30, BODY_H / 2 - 10), QPointF(-20, BODY_H / 2 - 10)]))
    p.drawPolyline(QPolygonF([QPointF(46, BODY_H / 2 - 6), QPointF(34, BODY_H / 2 - 6),
                              QPointF(30, BODY_H / 2 - 10), QPointF(20, BODY_H / 2 - 10)]))
    p.restore()


def _circuitos(p, cor):
    """Trilhas de circuito acesas nas laterais do rosto, na faixa da casca entre a moldura e a tela."""
    p.save()
    p.setPen(QPen(cor, 1.5, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(cor)
    for side in (-1, 1):
        x = side * (BODY_W / 2 - 6)
        p.drawPolyline(QPolygonF([QPointF(x, -22), QPointF(x, -6), QPointF(x - side * 3, -2), QPointF(x - side * 3, 14)]))
        for y in (-22, 14):
            p.drawEllipse(QPointF(x if y < 0 else x - side * 3, y), 1.8, 1.8)
    p.restore()


def _headset_arco(p, cor):
    """Arco do headset neural, por cima da cabeça e atrás dela."""
    p.save()
    p.setPen(QPen(cor, 4, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(-BODY_W / 2 - 4, -BODY_H / 2 - 9, BODY_W + 8, 60), 20 * 16, 140 * 16)
    p.restore()


def _headset_conchas(p, cor, a):
    """Conchas do headset nos dois lados, com faixa ciano, e o microfone saindo da esquerda."""
    p.save()
    luz = QColor(a.olho)
    for side in (-1, 1):
        concha = QRectF(side * (BODY_W / 2 + 1) - 7, -16, 14, 30)
        p.setPen(QPen(cor.darker(170), 1.5))
        p.setBrush(cor)
        p.drawRoundedRect(concha, 6, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(luz)
        p.drawRoundedRect(QRectF(concha.center().x() - 1.5, -9, 3, 16), 1.5, 1.5)
    p.setPen(QPen(cor, 2.5, Qt.SolidLine, Qt.RoundCap))
    p.setBrush(Qt.NoBrush)
    boca = QPainterPath(QPointF(-BODY_W / 2 - 1, 10))
    boca.quadTo(QPointF(-BODY_W / 2 - 2, 30), QPointF(-34, 32))
    p.drawPath(boca)
    p.setPen(Qt.NoPen)
    p.setBrush(luz)
    p.drawEllipse(QPointF(-33, 32), 3, 3)
    p.restore()


def _cursor(p, cor, agora):
    """Cursor de terminal piscando no canto da tela: o indicador de que ele está "ligado"."""
    if int(agora * 1.6) % 2:
        return
    p.save()
    p.setPen(Qt.NoPen)
    p.setBrush(cor)
    p.drawRect(QRectF(BODY_W / 2 - 24, BODY_H / 2 - 18, 8, 3))
    p.restore()


def _cafe(p, cor, agora):
    """Caneca de café virtual flutuando ao lado, em contorno de luz, com vapor subindo: hora do descanso."""
    p.save()
    x0, y0 = -BODY_W / 2 - 24, BODY_H / 2 - 30 + 2 * math.sin(agora * 1.3)
    vidro = QColor(cor)
    vidro.setAlpha(60)
    p.setPen(QPen(cor, 2))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QRectF(x0 + 15, y0 + 6, 10, 11))    # alça
    p.setBrush(vidro)
    p.drawRoundedRect(QRectF(x0, y0, 19, 22), 4, 4)
    cafe = QColor("#916bff")
    cafe.setAlpha(170)
    p.setPen(Qt.NoPen)
    p.setBrush(cafe)
    p.drawRoundedRect(QRectF(x0 + 3, y0 + 6, 13, 13), 2, 2)   # o café, em luz violeta
    for i in range(2):
        t = (agora * 0.6 + i * 0.5) % 1.0
        vapor = QColor(cor)
        vapor.setAlpha(int(160 * (1 - t)))
        p.setPen(QPen(vapor, 1.5, Qt.SolidLine, Qt.RoundCap))
        x = x0 + 5 + i * 5 + 2 * math.sin(t * math.tau)
        p.drawLine(QPointF(x, y0 - 2 - 12 * t), QPointF(x + 1, y0 - 6 - 12 * t))
    p.restore()


def _travesseiro(p, cor):
    """Travesseiro fofo atrás da parte de baixo do corpo, aparecendo dos dois lados."""
    p.save()
    fronha = QColor(cor)
    fronha.setAlpha(220)
    p.setPen(QPen(cor.lighter(140), 2))
    p.setBrush(fronha)
    p.drawRoundedRect(QRectF(-BODY_W / 2 - 14, BODY_H / 2 - 26, BODY_W + 28, 24), 12, 12)
    p.setPen(QPen(cor.lighter(160), 1.5, Qt.DashLine))
    p.drawLine(QPointF(-BODY_W / 2 - 8, BODY_H / 2 - 14), QPointF(BODY_W / 2 + 8, BODY_H / 2 - 14))   # costura
    p.restore()


def _notas(p, cor, agora):
    """Três notinhas musicais subindo em volta da cabeça, cada uma no seu tempo."""
    p.save()
    for i in range(3):
        t = (agora * 0.35 + i / 3) % 1.0
        x = (-1 if i % 2 else 1) * (BODY_W / 2 + 4) + 6 * math.sin(t * math.tau + i)
        y = -10 - 50 * t
        nota = QColor(cor)
        nota.setAlpha(int(255 * min(1.0, t * 4) * (1.0 - t)))
        p.setPen(QPen(nota, 2, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(nota)
        p.drawEllipse(QPointF(x, y), 3.6, 2.8)
        p.drawLine(QPointF(x + 3, y), QPointF(x + 3, y - 11))
        p.drawLine(QPointF(x + 3, y - 11), QPointF(x + 8, y - 8))          # bandeirinha
    p.restore()


def _balao(p, cor, agora):
    """Balãozinho de "digitando..." no alto, à direita: ele também está conversando."""
    p.save()
    balao = QRectF(BODY_W / 2 - 34, -BODY_H / 2 - 30, 40, 22)
    fundo = QColor(cor)
    fundo.setAlpha(230)
    p.setPen(Qt.NoPen)
    p.setBrush(fundo)
    p.drawRoundedRect(balao, 10, 10)
    p.drawPolygon(QPolygonF([QPointF(balao.left() + 8, balao.bottom() - 1), QPointF(balao.left() + 18, balao.bottom() - 1),
                             QPointF(balao.left() + 6, balao.bottom() + 7)]))   # rabinho
    for i in range(3):
        ponto = QColor("#202631")
        ponto.setAlpha(255 if int(agora * 3) % 4 > i else 80)
        p.setBrush(ponto)
        p.drawEllipse(QPointF(balao.center().x() - 9 + i * 9, balao.center().y()), 2.6, 2.6)
    p.restore()


def draw_zzz(p, cx, cy, now, cor=EYE):
    """Zs subindo do canto de cima do corpo, crescendo, balançando e sumindo."""
    for i in range(ZZZ_COUNT):
        t = ((now / ZZZ_PERIOD) + i / ZZZ_COUNT) % 1.0     # 0 nasce ... 1 some
        x = cx + BODY_W * 0.32 + 34 * t + 5 * math.sin(t * math.tau * 1.5)
        y = cy - BODY_H * 0.42 - 44 * t       # sobe até ~12 px do topo da janela
        size = 8 + 9 * t
        alpha = int(255 * min(1.0, t * 5) * (1.0 - t) ** 0.6)
        color = QColor(cor)
        color.setAlpha(alpha)
        p.save()
        p.translate(x, y)
        p.rotate(-12 + 10 * math.sin(t * math.tau))
        p.setPen(color)
        p.setFont(QFont("Consolas", int(size), QFont.Bold))
        p.drawText(QRectF(-20, -20, 40, 40), Qt.AlignCenter, "Z")
        p.restore()
