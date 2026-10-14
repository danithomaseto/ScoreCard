"""Gera os arquivos visuais do aplicativo: o icone do .exe e a tela de
abertura.

Nao faz parte do programa e nao roda junto com ele — e so pra
regenerar os arquivos de `ui/assets/` quando o desenho mudar. Precisa
do Pillow instalado (`pip install Pillow`), que de proposito nao esta
no requirements.txt: o app nao depende dele em tempo de execucao.

    python tools/gerar_icone.py

A marca e um alvo com a flecha no centro: fala de meta batida, que e o
assunto do sistema. As cores sao as mesmas da interface (os tokens
--yellow, --red e --bg do ui/style.css). O vermelho fica no miolo, onde
significa "o centro da meta" — e nao no lugar onde o app usa vermelho
pra dizer "abaixo da meta".
"""

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

AMARELO = (255, 204, 0)
VERMELHO = (212, 5, 17)
ESCURO = (11, 14, 26)
CINZA = (148, 163, 184)
CLARO = (228, 231, 236)

B = 1024
DESTINO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "assets")


def desenhar_alvo():
    img = Image.new("RGBA", (B, B), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([30, 30, B - 30, B - 30], radius=220, fill=AMARELO)

    cx, cy = int(B * 0.46), int(B * 0.54)
    for raio, cor in ((300, ESCURO), (206, AMARELO), (116, VERMELHO)):
        d.ellipse([cx - raio, cy - raio, cx + raio, cy + raio], fill=cor)

    # Flecha saindo do centro pro canto superior direito.
    d.line([cx, cy, B - 190, 190], fill=ESCURO, width=76)
    d.polygon([(B - 140, 140), (B - 150, 320), (B - 320, 310)], fill=ESCURO)
    return img


def fonte(tamanho, italico=False):
    candidatos = (
        ("C:/Windows/Fonts/segoeuiz.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-BoldItalic.ttf")
        if italico else
        ("C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    )
    for caminho in candidatos:
        if os.path.isfile(caminho):
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def _brilho(tamanho, centro, raio, cor, forca):
    """Camada RGBA com um brilho redondo: uma elipse desfocada, que some
    de verdade antes da borda (sem faixa retangular no fundo)."""
    alfa = Image.new("L", tamanho, 0)
    ImageDraw.Draw(alfa).ellipse(
        [centro[0] - raio * 0.6, centro[1] - raio * 0.45, centro[0] + raio * 0.6, centro[1] + raio * 0.45],
        fill=int(255 * forca))
    alfa = alfa.filter(ImageFilter.GaussianBlur(raio * 0.35))
    camada = Image.new("RGBA", tamanho, cor + (0,))
    camada.putalpha(alfa)
    return camada


def desenhar_splash():
    """A tela que o ScoreCard.exe mostra enquanto o app abre: o mesmo
    desenho da abertura do app (logo, barras com a tendencia, titulo e
    slogan), desenhada em dobro e reduzida para ficar lisa. A faixa de
    baixo fica livre para o texto do lancador (build.spec, text_pos)."""
    largura, altura, x2 = 520, 300, 2
    L, A = largura * x2, altura * x2
    img = Image.new("RGBA", (L, A), ESCURO + (255,))
    img.alpha_composite(_brilho((L, A), (L // 2, int(A * 0.36)), int(L * 0.5), AMARELO, 0.30))
    img.alpha_composite(_brilho((L, A), (L // 2, int(A * 1.05)), int(L * 0.6), VERMELHO, 0.22))

    # Grade fina, mais forte no meio.
    grade = Image.new("RGBA", (L, A), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grade)
    for x in range(0, L, 48 * x2 // 2):
        dg.line([(x, 0), (x, A)], fill=(255, 255, 255, 10), width=1)
    for y in range(0, A, 48 * x2 // 2):
        dg.line([(0, y), (L, y)], fill=(255, 255, 255, 10), width=1)
    meio = Image.new("L", (L, A), 0)
    ImageDraw.Draw(meio).ellipse([L * 0.15, A * 0.05, L * 0.85, A * 0.95], fill=255)
    meio = meio.filter(ImageFilter.GaussianBlur(L * 0.12))
    grade.putalpha(Image.composite(grade.getchannel("A"), Image.new("L", (L, A), 0), meio))
    img.alpha_composite(grade)

    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, L, 4 * x2], fill=AMARELO)

    # Logo DHL: amarelo com o vermelho em italico.
    f_logo = fonte(30 * x2, italico=True)
    texto_w = d.textlength("DHL", font=f_logo)
    lw, lh = int(texto_w + 34 * x2), 50 * x2
    lx, ly = (L - lw) // 2, 34 * x2
    sombra = _brilho((L, A), (L // 2, ly + lh // 2), int(lw * 1.1), AMARELO, 0.45)
    img.alpha_composite(sombra)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=7 * x2, fill=AMARELO)
    d.text((L // 2, ly + lh // 2 + x2), "DHL", font=f_logo, fill=VERMELHO, anchor="mm")

    # Seis barras (os seis indicadores) e a linha de tendencia.
    base_y, bx0, bw, gap = 152 * x2, (L - (6 * 18 + 5 * 8) * x2) // 2, 18 * x2, 8 * x2
    alturas = (0.42, 0.64, 0.52, 0.78, 0.70, 0.96)
    topos = []
    for i, h in enumerate(alturas):
        x = bx0 + i * (bw + gap)
        topo = base_y - int(h * 56 * x2)
        cor_cima, cor_baixo = ((74, 222, 128), (22, 163, 74)) if i == 5 else ((255, 216, 77), (230, 184, 0))
        grad = Image.linear_gradient("L").resize((bw, base_y - topo))
        barra = Image.composite(Image.new("RGBA", grad.size, cor_baixo + (255,)),
                                Image.new("RGBA", grad.size, cor_cima + (255,)), grad)
        mascara = Image.new("L", grad.size, 0)
        ImageDraw.Draw(mascara).rounded_rectangle([0, 0, bw - 1, grad.size[1] + 6 * x2], radius=3 * x2, fill=255)
        img.paste(barra, (x, topo), mascara)
        topos.append((x + bw // 2, topo - 10 * x2))
    d = ImageDraw.Draw(img)
    d.line([(bx0 - 4 * x2, base_y + 2 * x2), (bx0 + 6 * bw + 5 * gap + 4 * x2, base_y + 2 * x2)],
           fill=(255, 255, 255, 40), width=2 * x2)
    d.line(topos, fill=(255, 255, 255, 255), width=3 * x2, joint="curve")
    px, py = topos[-1]
    d.ellipse([px - 9 * x2, py - 9 * x2, px + 9 * x2, py + 9 * x2], outline=(255, 255, 255, 90), width=2 * x2)
    d.ellipse([px - 4 * x2, py - 4 * x2, px + 4 * x2, py + 4 * x2], fill=(255, 255, 255, 255))

    # Titulo e slogan.
    f_titulo = fonte(36 * x2)
    w_score = d.textlength("Score ", font=f_titulo)
    w_total = w_score + d.textlength("Card", font=f_titulo)
    tx, ty = (L - w_total) / 2, 168 * x2
    d.text((tx, ty), "Score ", font=f_titulo, fill=CLARO)
    d.text((tx + w_score, ty), "Card", font=f_titulo, fill=AMARELO)
    f_sub = fonte(9 * x2)
    slogan = "EXCELLENCE.  SIMPLY  DELIVERED."
    espaco = 3 * x2
    w_sub = sum(d.textlength(c, font=f_sub) for c in slogan) + espaco * (len(slogan) - 1)
    x = (L - w_sub) / 2
    for c in slogan:
        d.text((x, 222 * x2), c, font=f_sub, fill=CINZA)
        x += d.textlength(c, font=f_sub) + espaco

    # Faixa de baixo: linha fina; o lancador escreve o andamento por cima.
    d.line([(18 * x2, 262 * x2), (L - 18 * x2, 262 * x2)], fill=(255, 255, 255, 18), width=x2)
    return img.resize((largura, altura), Image.LANCZOS).convert("RGB")


def main():
    marca = desenhar_alvo()
    # Os seis tamanhos que o Windows usa: sem o de 16, a barra de
    # titulo e a lista de arquivos mostram uma reducao borrada.
    tamanhos = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    marca.save(os.path.join(DESTINO, "scorecard.ico"), format="ICO", sizes=tamanhos)
    marca.resize((256, 256), Image.LANCZOS).save(os.path.join(DESTINO, "scorecard.png"))
    desenhar_splash().save(os.path.join(DESTINO, "splash.png"))
    print("gerados em", DESTINO)


if __name__ == "__main__":
    main()
