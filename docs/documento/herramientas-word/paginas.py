"""Arma láminas con las páginas del PDF donde aparecen ciertos textos, para revisarlas a ojo.

Uso:
    python paginas.py DOC.pdf SALIDA_PREFIJO "texto 1" "texto 2" ... [--todas] [--desde "A" --hasta "B"]

  - Por cada texto toma la primera página que lo contiene (con --todas, todas).
  - Con --desde/--hasta toma el rango de páginas entre el primer "A" y el primer "B" posterior.
  - Guarda SALIDA_PREFIJO-1.png, -2.png, ... con 8 páginas por lámina (4 x 2) y lista
    qué página quedó en cada lámina.
Requiere PyMuPDF y Pillow.
"""
import argparse
import pymupdf
from PIL import Image

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf'); ap.add_argument('salida')
    ap.add_argument('textos', nargs='*')
    ap.add_argument('--todas', action='store_true')
    ap.add_argument('--desde'); ap.add_argument('--hasta')
    ap.add_argument('--dpi', type=int, default=48)
    a = ap.parse_args()
    d = pymupdf.open(a.pdf)
    N = d.page_count
    textos = [d[i].get_text() for i in range(N)]
    pags = []
    for t in a.textos:
        hits = [i + 1 for i in range(N) if t in textos[i]]
        print(f'{t!r}: {hits[:10]}')
        pags += hits if a.todas else hits[:1]
    if a.desde:
        i0 = next(i for i in range(N) if a.desde in textos[i])
        i1 = next(i for i in range(i0 + 1, N) if a.hasta in textos[i]) if a.hasta else i0
        pags += list(range(i0 + 1, i1 + 2))
    pags = list(dict.fromkeys(pags))
    for k in range(0, len(pags), 8):
        ims = []
        for p in pags[k:k + 8]:
            pm = d[p - 1].get_pixmap(dpi=a.dpi)
            ims.append(Image.frombytes('RGB', (pm.width, pm.height), pm.samples))
        w, h = ims[0].size
        M = Image.new('RGB', (w * 4, h * 2), 'white')
        for i, im in enumerate(ims):
            M.paste(im, ((i % 4) * w, (i // 4) * h))
        nombre = f'{a.salida}-{k // 8 + 1}.png'
        M.save(nombre)
        print(nombre, pags[k:k + 8])
    print('páginas del PDF:', N)

if __name__ == '__main__':
    main()
