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

from PIL import Image, ImageDraw, ImageFont

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


def fonte(tamanho):
    for caminho in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
    ):
        if os.path.isfile(caminho):
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()


def desenhar_splash(marca):
    largura, altura = 460, 260
    img = Image.new("RGB", (largura, altura), ESCURO)
    d = ImageDraw.Draw(img)
    # Faixa amarela no topo, como a barra do aplicativo.
    d.rectangle([0, 0, largura, 6], fill=AMARELO)

    icone = marca.resize((92, 92), Image.LANCZOS)
    img.paste(icone, (largura // 2 - 46, 50), icone)

    def centralizado(y, texto, tamanho, cor):
        f = fonte(tamanho)
        d.text(((largura - d.textlength(texto, font=f)) / 2, y), texto, font=f, fill=cor)

    centralizado(160, "Score Card", 30, CLARO)
    centralizado(200, "Abrindo o aplicativo...", 15, CINZA)
    return img


def main():
    marca = desenhar_alvo()
    # Os seis tamanhos que o Windows usa: sem o de 16, a barra de
    # titulo e a lista de arquivos mostram uma reducao borrada.
    tamanhos = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    marca.save(os.path.join(DESTINO, "scorecard.ico"), format="ICO", sizes=tamanhos)
    marca.resize((256, 256), Image.LANCZOS).save(os.path.join(DESTINO, "scorecard.png"))
    desenhar_splash(marca).save(os.path.join(DESTINO, "splash.png"))
    print("gerados em", DESTINO)


if __name__ == "__main__":
    main()
