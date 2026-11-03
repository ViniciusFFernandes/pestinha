"""
FIGURINO - os acessórios que o pet pega e larga conforme a situação.

O pet.json diz quais acessórios são de qual situação ("aparencia" -> "situacoes"), por exemplo
{"jogo": ["headset"], "programando": ["cafe"], "parado": ["travesseiro"]}. Acessório que não está
em nenhuma situação fica sempre no corpo, como antes.

Ele não veste na hora: a cada segundo da situação há uma chance de pegar (dá um tempinho natural),
e algumas coisas são passageiras (o café dura uns minutos e depois ele só pega de novo mais tarde).
Quando a situação acaba, ele larga depois de alguns segundos. Só decide; quem desenha é o rosto.
"""

import random

# situação -> (chance por segundo de pegar, duração (min, max) em s ou None = enquanto durar, pausa depois em s)
REGRAS = {
    "jogo":        (0.30,  None,        0),
    "musica":      (0.20,  None,        0),
    "conversa":    (1 / 40, (15, 40),   60),
    "programando": (1 / 300, (60, 240), 300),
    "parado":      (0.05,  None,        0),
    "sossego":     (0.10,  None,        0),
}
PARADO_APOS = 300            # s sem teclado nem mouse: pega o travesseiro
LARGA_DEPOIS = (3.0, 10.0)   # s: quando a situação acaba, ainda segura um pouquinho


def situacoes_agora(activity, idle_seconds, emotion):
    """Quais situações valem neste instante, a partir do que você faz e do que ele sente."""
    agora = set()
    if activity == "GAMING":
        agora.add("jogo")
    if activity == "MUSIC":
        agora.add("musica")
    if activity == "SOCIAL":
        agora.add("conversa")
    if activity in ("PROGRAMMING", "DESIGNING"):
        agora.add("programando")
    if activity == "AWAY" or idle_seconds >= PARADO_APOS or emotion in ("dormindo", "sonolento"):
        agora.add("parado")
    if emotion == "contente":
        agora.add("sossego")
    return agora


class Figurino:
    """Decide o que o pet está vestindo agora, entre os acessórios de situação do pet.json."""

    def __init__(self, situacoes, rng=None):
        """`situacoes`: {situação: (acessório, ...)}; situação sem regra conhecida é ignorada."""
        self.situacoes = {s: tuple(nomes) for s, nomes in dict(situacoes).items() if s in REGRAS}
        self.rng = rng or random.Random()
        self.ate = {}            # situação vestida -> até quando (inf = enquanto a situação durar)
        self.larga_em = {}       # situação que acabou -> quando ele larga
        self.pausa_ate = {}      # situação passageira -> só pega de novo depois disso

    def tick(self, now, dt, activity, idle_seconds, emotion):
        """Avança `dt` segundos e devolve o conjunto de acessórios vestidos."""
        valendo = situacoes_agora(activity, idle_seconds, emotion)
        for situacao in self.situacoes:
            chance, duracao, pausa = REGRAS[situacao]
            if situacao in self.ate:
                acabou_o_tempo = now >= self.ate[situacao]
                if situacao not in valendo and situacao not in self.larga_em:
                    self.larga_em[situacao] = now + self.rng.uniform(*LARGA_DEPOIS)
                elif situacao in valendo:
                    self.larga_em.pop(situacao, None)
                if acabou_o_tempo or now >= self.larga_em.get(situacao, float("inf")):
                    del self.ate[situacao]
                    self.larga_em.pop(situacao, None)
                    if pausa:
                        self.pausa_ate[situacao] = now + pausa
            elif situacao in valendo and now >= self.pausa_ate.get(situacao, 0.0) \
                    and self.rng.random() < chance * dt:
                self.ate[situacao] = now + self.rng.uniform(*duracao) if duracao else float("inf")
        return frozenset(nome for s in self.ate for nome in self.situacoes[s])
