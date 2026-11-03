"""
Desenha os memes do PATCH em pets/patch/memes/<emoção>/ e pets/patch/memes/trabalhando/.

Cada meme é uma legenda grande em cima e uma cena embaixo: o próprio PATCH (desenhado pelo mesmo
código do pet, body/desenho_rosto.py) e um objeto de programador (terminal, erro, SQL, café...).
Humor de dev com textos próprios; nada de imagem de terceiros. Rode de novo para refazer tudo.

Precisa das fontes do sistema: rode no Windows (não no modo offscreen).
"""
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QImage, QPainter, QPen  # noqa: E402

from pestinha import config  # noqa: E402
from pestinha.body.desenho_rosto import aparencia_de, draw_face  # noqa: E402
from pestinha.core.emotion import EYE_SHAPES  # noqa: E402
from pestinha.paths import Paths  # noqa: E402

LADO = 1024
DESTINO = RAIZ / "pets" / "patch" / "memes"
FUNDO, GRADE = QColor("#11151c"), QColor("#1a2130")
CIANO, VIOLETA, VERDE = QColor("#32dceb"), QColor("#916bff"), QColor("#8be36b")
BRANCO, GRAFITE, VERMELHO, AMARELO = QColor("#e8faff"), QColor("#202631"), QColor("#ff5c7a"), QColor("#ffd166")

# (pasta, arquivo, linha de cima, linha de baixo (destaque), rosto, vestindo, cena, textos da cena)
MEMES = [
    ("feliz", "patch_feliz_01", "FUNCIONOU DE PRIMEIRA.", "AGORA EU DESCONFIO.", "feliz", (),
     "terminal", ["$ php artisan test", "", "Tests: 42 passed", "Time: 0.31s", "", "✓ BUILD OK"]),
    ("feliz", "patch_feliz_02", "DEPLOY NA SEXTA", "E NADA QUEBROU.", "feliz", (), "fogos", []),
    ("feliz", "patch_feliz_03", "0 ERRORS. 0 WARNINGS.", "QUEM É VOCÊ?", "feliz", (),
     "terminal", ["> npm run build", "", "compiled successfully", "0 errors", "0 warnings", "", "...sério?"]),
    ("contente", "patch_contente_01", "CAFÉ QUENTE,", "CÓDIGO LIMPO.", "contente", ("cafe",), "cafe", []),
    ("contente", "patch_contente_02", "COMMIT FEITO.", "PAZ INTERIOR.", "contente", (),
     "terminal", ["$ git commit -m", "  \"funciona\"", "", "[main 4f2a9c1]", "1 file changed", "", "$ _"]),
    ("curioso", "patch_curioso_01", "O QUE ACONTECE", "SE EU APERTAR AQUI?", "curioso", (), "botao", []),
    ("curioso", "patch_curioso_02", "QUEM ESCREVEU ISSO?", "git blame: VOCÊ.", "curioso", (),
     "terminal", ["$ git blame", "  relatorio.php", "", "a91f (você) 2019", "a91f (você) 2019", "a91f (você) 2019"]),
    ("bravo", "patch_bravo_01", "UPDATE SEM WHERE.", "DE NOVO.", "bravo", (),
     "sql", ["UPDATE clientes", "SET ativo = 0;", "", "-- 48.213 rows", "-- affected"]),
    ("bravo", "patch_bravo_02", "QUEM DEIXOU", "var_dump EM PRODUÇÃO?", "bravo", (),
     "erro", ["array(3) {", " [\"senha\"]=>", "  string(6)...", "}"]),
    ("bravo", "patch_bravo_03", "FUNCIONA NA MINHA MÁQUINA.", "ENTÃO ENVIA ELA PRO CLIENTE.", "bravo", (),
     "erro", ["Erro 500", "Internal Server", "Error", "", "(só no servidor)"]),
    ("triste", "patch_triste_01", "O CAFÉ ACABOU.", "O BUG NÃO.", "triste", (), "cafe_vazio", []),
    ("triste", "patch_triste_02", "3 HORAS DEPURANDO.", "ERA UM PONTO E VÍRGULA.", "triste", (),
     "terminal", ["Parse error:", "syntax error,", "unexpected '}'", "on line 1337", "", "  ;"]),
    ("pensando", "patch_pensando_01", "99 BUGS NO CÓDIGO.", "CORRIGI UM. AGORA SÃO 117.", "pensando", (),
     "terminal", ["bugs = 99", "bugs -= 1", "", ">>> bugs", "117", "", "???"]),
    ("pensando", "patch_pensando_02", "O MAIS DIFÍCIL DA PROGRAMAÇÃO:", "DAR NOME ÀS VARIÁVEIS.", "pensando", (),
     "terminal", ["$dados", "$dados2", "$dadosNovo", "$dadosNovoFinal", "$dadosAgoraVai", "$x"]),
    ("sarcastico", "patch_sarcastico_01", "ISSO NÃO É GAMBIARRA.", "É ARQUITETURA ALTERNATIVA.", "sarcastico", (),
     "terminal", ["if ($x == 1) {", "  // não mexe", "  sleep(3);", "  return true;", "}", "// funciona"]),
    ("sarcastico", "patch_sarcastico_02", "CLARO QUE TEM DOCUMENTAÇÃO.", "ESTÁ NA SUA CABEÇA.", "sarcastico", (),
     "terminal", ["README.md", "", "# Projeto", "", "TODO: escrever", "(2017)"]),
    ("sarcastico", "patch_sarcastico_03", "!important", "RESOLVE TUDO. CONFIA.", "sarcastico", (),
     "terminal", [".botao {", "  color: red", "    !important;", "  margin: 0", "    !important;", "}"]),
    ("sonolento", "patch_sonolento_01", "SÓ MAIS UM BUG", "E EU VOU DORMIR.", "sonolento", ("travesseiro",), "relogio", []),
    ("sonolento", "patch_sonolento_02", "MODO ECONOMIA DE ENERGIA:", "ATIVADO.", "sonolento", ("travesseiro",), "bateria", []),
    ("trabalhando", "patch_trabalho_01", "ESTÁ FUNCIONANDO.", "NÃO MEXE.", "pensando", (),
     "terminal", ["// NÃO APAGAR", "// ninguém sabe", "// por que funciona", "", "$ok = true;"]),
    ("trabalhando", "patch_trabalho_02", "SELECT * FROM", "problemas;", "pensando", ("cafe",),
     "sql", ["SELECT *", "FROM problemas", "WHERE resolvido", "  = 0;", "", "-- 1.284 rows"]),
    ("trabalhando", "patch_trabalho_03", "O CLIENTE PEDIU", "SÓ UM AJUSTEZINHO.", "sarcastico", (),
     "erro", ["Novo chamado:", "\"muda tudo,", "mas é rapidinho\"", "", "Prazo: hoje"]),
    ("trabalhando", "patch_trabalho_04", "CTRL+C, CTRL+V:", "ENGENHARIA DE SOFTWARE.", "contente", (),
     "terminal", ["// copiado do", "// fórum, 2011", "", "function x() {", "  // mágica", "}"]),
    ("trabalhando", "patch_trabalho_05", "LEGADO EM PHP 5.", "AINDA RODANDO. RESPEITA.", "sarcastico", (),
     "terminal", ["mysql_connect(", "  $host, $user", ");", "", "uptime: 11 anos"]),
    ("trabalhando", "patch_trabalho_06", "TESTE EM PRODUÇÃO", "É TESTE COM USUÁRIO REAL.", "feliz", (),
     "erro", ["Usuário:", "\"cliquei e", "sumiu tudo\"", "", "Você: interessante"]),
]


def fonte(tamanho, mono=False):
    f = QFont("Consolas" if mono else "Segoe UI Black", tamanho)
    f.setBold(True)
    return f


def texto_que_cabe(p, texto, rect, cor, tamanho, mono=False):
    """Escreve centralizado, diminuindo a letra até caber na largura."""
    while tamanho > 20 and QFontMetrics(fonte(tamanho, mono)).horizontalAdvance(texto) > rect.width():
        tamanho -= 2
    p.setFont(fonte(tamanho, mono))
    p.setPen(cor)
    p.drawText(rect, Qt.AlignCenter, texto)


def fundo(p):
    p.fillRect(0, 0, LADO, LADO, FUNDO)
    p.setPen(QPen(GRADE, 1))
    for i in range(0, LADO, 32):
        p.drawLine(i, 0, i, LADO)
        p.drawLine(0, i, LADO, i)
    p.setPen(QPen(CIANO, 6))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(14, 14, LADO - 28, LADO - 28), 28, 28)


def janela(p, rect, titulo_cor, linhas, cor_texto=VERDE, titulo=""):
    """Janela de terminal/editor: barra com três bolinhas e linhas em fonte mono."""
    p.setPen(QPen(titulo_cor, 4))
    p.setBrush(GRAFITE)
    p.drawRoundedRect(rect, 18, 18)
    p.setPen(Qt.NoPen)
    p.setBrush(titulo_cor.darker(260))
    p.drawRoundedRect(QRectF(rect.left() + 2, rect.top() + 2, rect.width() - 4, 46), 16, 16)
    for i, c in enumerate((VERMELHO, AMARELO, VERDE)):
        p.setBrush(c)
        p.drawEllipse(QPointF(rect.left() + 30 + i * 28, rect.top() + 25), 9, 9)
    if titulo:
        p.setPen(BRANCO)
        p.setFont(fonte(18, True))
        p.drawText(QRectF(rect.left(), rect.top() + 4, rect.width() - 20, 42), Qt.AlignRight | Qt.AlignVCenter, titulo)
    y = rect.top() + 72
    altura = min(48, (rect.height() - 90) / max(1, len(linhas)))
    for linha in linhas:
        texto_que_cabe(p, linha, QRectF(rect.left() + 26, y, rect.width() - 52, altura), cor_texto, 30, mono=True)
        y += altura


def cena(p, tipo, textos):
    """O objeto do lado direito do PATCH."""
    area = QRectF(540, 430, 440, 470)
    if tipo == "terminal":
        janela(p, area, CIANO, textos, titulo="terminal")
    elif tipo == "sql":
        janela(p, area, VIOLETA, textos, cor_texto=CIANO, titulo="mysql")
    elif tipo == "erro":
        p.setPen(QPen(VERMELHO, 5))
        p.setBrush(GRAFITE)
        p.drawRoundedRect(area, 18, 18)
        texto_que_cabe(p, "⚠", QRectF(area.left(), area.top() + 20, area.width(), 90), VERMELHO, 80)
        y = area.top() + 130
        for linha in textos:
            texto_que_cabe(p, linha, QRectF(area.left() + 24, y, area.width() - 48, 56), BRANCO, 34, mono=True)
            y += 58
    elif tipo in ("cafe", "cafe_vazio"):
        caneca = QRectF(640, 560, 220, 260)
        p.setPen(QPen(CIANO, 8))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(830, 620, 110, 130))
        p.setBrush(GRAFITE)
        p.drawRoundedRect(caneca, 30, 30)
        if tipo == "cafe":
            p.setPen(Qt.NoPen)
            p.setBrush(VIOLETA)
            p.drawRoundedRect(QRectF(660, 600, 180, 200), 20, 20)
            p.setPen(QPen(BRANCO, 7, Qt.SolidLine, Qt.RoundCap))
            for x in (700, 750, 800):
                p.drawArc(QRectF(x - 20, 440, 40, 90), 90 * 16, 180 * 16)
        else:
            texto_que_cabe(p, "vazio", QRectF(640, 650, 220, 80), CIANO, 44, mono=True)
    elif tipo == "botao":
        p.setPen(QPen(BRANCO, 6))
        p.setBrush(GRAFITE)
        p.drawRoundedRect(QRectF(620, 720, 280, 110), 20, 20)
        p.setBrush(VERMELHO)
        p.drawEllipse(QRectF(680, 600, 160, 150))
        texto_que_cabe(p, "NÃO APERTE", QRectF(560, 850, 400, 60), AMARELO, 40)
        texto_que_cabe(p, "DROP DATABASE", QRectF(620, 760, 280, 50), BRANCO, 26, mono=True)
    elif tipo == "fogos":
        p.setPen(Qt.NoPen)
        for cx, cy, cor in ((700, 560, CIANO), (880, 700, VIOLETA), (760, 820, VERDE)):
            for k in range(14):
                ang = k * math.tau / 14
                p.setBrush(cor)
                p.drawEllipse(QPointF(cx + 90 * math.cos(ang), cy + 90 * math.sin(ang)), 10, 10)
                p.setBrush(BRANCO)
                p.drawEllipse(QPointF(cx + 50 * math.cos(ang), cy + 50 * math.sin(ang)), 6, 6)
        janela(p, QRectF(560, 410, 400, 150), VERDE, ["deploy: OK ✓"])
    elif tipo == "relogio":
        p.setPen(QPen(CIANO, 8))
        p.setBrush(GRAFITE)
        p.drawEllipse(QRectF(620, 480, 300, 300))
        p.setPen(QPen(BRANCO, 10, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(770, 630), QPointF(770, 530))
        p.drawLine(QPointF(770, 630), QPointF(840, 660))
        texto_que_cabe(p, "03:17", QRectF(560, 810, 420, 80), VIOLETA, 64, mono=True)
    elif tipo == "bateria":
        p.setPen(QPen(BRANCO, 8))
        p.setBrush(GRAFITE)
        p.drawRoundedRect(QRectF(600, 560, 320, 160), 22, 22)
        p.setBrush(BRANCO)
        p.drawRoundedRect(QRectF(922, 605, 26, 70), 8, 8)
        p.setPen(Qt.NoPen)
        p.setBrush(VERMELHO)
        p.drawRoundedRect(QRectF(620, 580, 50, 120), 10, 10)
        texto_que_cabe(p, "3%", QRectF(600, 740, 320, 90), VERMELHO, 70, mono=True)


def desenhar_meme(aparencia, cima, baixo, emocao, vestindo, tipo, textos):
    img = QImage(LADO, LADO, QImage.Format_ARGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    fundo(p)
    texto_que_cabe(p, cima, QRectF(50, 70, LADO - 100, 130), BRANCO, 92)
    texto_que_cabe(p, baixo, QRectF(50, 210, LADO - 100, 130), CIANO, 92)
    cena(p, tipo, textos)
    p.save()
    p.translate(290, 680)
    p.scale(3.0, 3.0)
    draw_face(p, dict(EYE_SHAPES[emocao]), (0.6, 0.0), 1.0, emocao, aparencia=aparencia, vestindo=frozenset(vestindo))
    p.restore()
    p.end()
    return img


def gerar(destino=DESTINO):
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    aparencia = aparencia_de(config.load_pet(Paths(root=RAIZ), "patch")["aparencia"])
    feitos = []
    for pasta, nome, cima, baixo, emocao, vestindo, tipo, textos in MEMES:
        (destino / pasta).mkdir(parents=True, exist_ok=True)
        img = desenhar_meme(aparencia, cima, baixo, emocao, vestindo, tipo, textos)
        caminho = destino / pasta / f"{nome}.webp"
        if not img.save(str(caminho), "WEBP", 88):
            caminho = caminho.with_suffix(".png")
            img.save(str(caminho))
        feitos.append(caminho)
    return feitos


if __name__ == "__main__":
    for caminho in gerar():
        print(caminho.relative_to(RAIZ))
