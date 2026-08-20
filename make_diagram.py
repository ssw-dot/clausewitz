#!/usr/bin/env python3
"""The architecture diagram, drawn from the code rather than described.

One thing has to survive being looked at for four seconds: **the model reads,
the code decides, and a gate stands between them.** Everything else on the page
is subordinate to showing that boundary, so the boundary is drawn as an actual
line across the image with the two worlds labelled on either side.

    python make_diagram.py architecture.png
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1800, 1240
F = "C:/Windows/Fonts/"

FONDO = (247, 249, 252)
TINTA = (17, 24, 39)
GRIS = (107, 114, 128)
LINEA = (156, 163, 175)
AZUL = (37, 99, 235)
AMBAR = (217, 119, 6)
VERDE = (5, 150, 105)
ROJO = (220, 38, 38)
MALVA = (109, 40, 217)


def f(nombre, tam):
    return ImageFont.truetype(F + nombre, tam)


def caja(d, xy, texto, sub=None, color=TINTA, relleno=(255, 255, 255),
         borde=None, ancho_borde=3, radio=14, fuente=None, img=None):
    x0, y0, x1, y1 = xy
    if img is not None:                       # sombra suave, da profundidad
        s = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle([x0 + 3, y0 + 6, x1 + 3, y1 + 6],
                                            radius=radio, fill=(15, 23, 42, 40))
        img.alpha_composite(s.filter(ImageFilter.GaussianBlur(7)))
    d.rounded_rectangle(xy, radius=radio, fill=relleno,
                        outline=borde or LINEA, width=ancho_borde)
    ft = fuente or f("segoeuib.ttf", 30)
    tw = d.textlength(texto, font=ft)
    cy = (y0 + y1) / 2 - (ft.size if sub else ft.size / 2) + (0 if sub else 2)
    d.text(((x0 + x1 - tw) / 2, cy), texto, font=ft, fill=color)
    if sub:
        fs = f("consola.ttf", 21)
        for i, linea in enumerate(sub):
            sw = d.textlength(linea, font=fs)
            d.text(((x0 + x1 - sw) / 2, cy + ft.size + 8 + i * 27), linea,
                   font=fs, fill=GRIS)


def flecha(d, desde, hasta, color=LINEA, ancho=3, etiqueta=None, lado="der"):
    x0, y0 = desde
    x1, y1 = hasta
    d.line([x0, y0, x1, y1], fill=color, width=ancho)
    if y1 > y0:                               # punta hacia abajo
        d.polygon([(x1, y1), (x1 - 10, y1 - 17), (x1 + 10, y1 - 17)], fill=color)
    else:                                     # punta hacia la derecha
        d.polygon([(x1, y1), (x1 - 17, y1 - 10), (x1 - 17, y1 + 10)], fill=color)
    if etiqueta:
        fe = f("segoeuib.ttf", 22)
        ew = d.textlength(etiqueta, font=fe)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx = 16 if lado == "der" else -ew - 16
        d.rectangle([mx + dx - 6, my - 15, mx + dx + ew + 6, my + 15],
                    fill=FONDO)
        d.text((mx + dx, my - 13), etiqueta, font=fe, fill=color)


def main(destino: Path) -> None:
    img = Image.new("RGBA", (W, H), FONDO + (255,))
    d = ImageDraw.Draw(img)

    d.text((70, 46), "Clausewitz", font=f("segoeuib.ttf", 54), fill=TINTA)
    d.text((70, 112), "The model reads. The code decides.",
           font=f("segoeuii.ttf", 30), fill=GRIS)

    cx = W // 2

    # ---- mundo del modelo -------------------------------------------------
    caja(d, (cx - 250, 185, cx + 250, 265), "a call for proposals",
         color=GRIS, relleno=(238, 242, 247), borde=LINEA, ancho_borde=2, img=img)
    flecha(d, (cx, 265), (cx, 320))

    caja(d, (cx - 300, 320, cx + 300, 452), "Strands Agent",
         sub=["Gemini via LiteLLM", "one tool: report_requirement"],
         color=MALVA, borde=MALVA, img=img)
    flecha(d, (cx, 452), (cx, 512))

    caja(d, (cx - 360, 512, cx + 360, 604), "Requirement",
         sub=['kind  ·  QUOTE  ·  value'],
         color=TINTA, borde=LINEA, ancho_borde=2, img=img)

    # ---- la frontera ------------------------------------------------------
    y = 648
    for x in range(60, W - 60, 22):
        d.line([x, y, x + 11, y], fill=(203, 213, 225), width=3)
    fb = f("segoeuib.ttf", 23)
    d.rectangle([cx - 250, y - 19, cx + 250, y + 19], fill=FONDO)
    t = "above: the model may be wrong    ·    below: it cannot decide"
    d.text((cx - d.textlength(t, font=fb) / 2, y - 14), t, font=fb, fill=(148, 163, 184))

    flecha(d, (cx, 604), (cx, 700))

    # ---- la puerta --------------------------------------------------------
    caja(d, (cx - 330, 700, cx + 330, 800), "quote_is_grounded()",
         sub=["is this sentence verbatim in the source?"],
         color=AMBAR, borde=AMBAR, fuente=f("consolab.ttf", 30), img=img)

    # ---- ramas ------------------------------------------------------------
    d.line([cx - 330, 750, cx - 620, 750], fill=ROJO, width=3)
    flecha(d, (cx - 620, 750), (cx - 620, 852), color=ROJO, etiqueta="no", lado="izq")
    d.line([cx, 800, cx, 852], fill=VERDE, width=3)
    flecha(d, (cx, 800), (cx, 852), color=VERDE, etiqueta="yes")

    caja(d, (cx - 830, 852, cx - 410, 976), "dropped",
         sub=["a hallucination cannot", "become a rejection"],
         color=ROJO, borde=ROJO, img=img)

    caja(d, (cx - 300, 852, cx + 300, 976), "screening.py",
         sub=["pure functions · no model · no network",
              "73 tests, none of which call a model"],
         color=AZUL, borde=AZUL, fuente=f("consolab.ttf", 30), img=img)

    # perfil entrando de lado
    # Alto 138 y no 118: con dos lineas de subtitulo el contenido mide 115 px
    # y la caja median 118, asi que el descendente de la ultima linea cruzaba
    # el borde. Se crece simetrica (10 arriba, 10 abajo) para que el centro no
    # se mueva y la flecha que entra siga alineada.
    caja(d, (cx + 360, 838, cx + 830, 976), "your profile",
         sub=["country · legal form", "can travel · needs cash"],
         color=GRIS, relleno=(238, 242, 247), borde=LINEA, ancho_borde=2, img=img)
    d.line([cx + 360, 907, cx + 310, 907], fill=LINEA, width=3)
    d.polygon([(cx + 300, 907), (cx + 317, 897), (cx + 317, 917)], fill=LINEA)

    # ---- veredictos -------------------------------------------------------
    d.line([cx, 976, cx, 1012], fill=LINEA, width=3)
    d.line([cx - 520, 1012, cx + 520, 1012], fill=LINEA, width=3)
    for x, txt, col, sub in ((cx - 520, "ELIGIBLE", VERDE, "every rule passed"),
                             (cx, "EXCLUDED", ROJO, "and here is the sentence"),
                             (cx + 520, "UNDECIDABLE", AMBAR, "a human should look")):
        flecha(d, (x, 1012), (x, 1052), color=col)
        fv = f("segoeuib.ttf", 34)
        tw = d.textlength(txt, font=fv)
        d.text((x - tw / 2, 1058), txt, font=fv, fill=col)
        fs = f("segoeuii.ttf", 22)
        sw = d.textlength(sub, font=fs)
        d.text((x - sw / 2, 1100), sub, font=fs, fill=GRIS)

    # nota que ata todo
    fn = f("segoeuib.ttf", 26)
    nota = ("Every ambiguity resolves to UNDECIDABLE, never to EXCLUDED.   "
            "Wrongly telling someone not to apply costs them a grant.")
    nw = d.textlength(nota, font=fn)
    d.text(((W - nw) / 2, H - 56), nota, font=fn, fill=(100, 116, 139))

    img.convert("RGB").save(destino, "PNG", optimize=True)
    print(f"OK  {destino}  ·  {W}x{H}  ·  {destino.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "architecture.png"))
