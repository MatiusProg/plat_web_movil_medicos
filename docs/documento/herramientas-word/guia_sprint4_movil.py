"""Arma la guía de estudio de la defensa del Sprint 4 con hoja tamaño celular.

Uso: python guia_sprint4_movil.py SALIDA.docx EJECUCIONES TMP [imprimir]
EJECUCIONES: salidas reales de pytest/flutter/API del 22/11/26. TMP: PNG intermedios.
El contenido está en guia_sprint4_contenido.py.
"""
import glob
import os
import re
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

SAL, EJEC, TMP = sys.argv[1:4]
IMPRIMIR = 'imprimir' in sys.argv[4:]   # hoja carta normal en vez de hoja de celular
AQUI = os.path.dirname(os.path.abspath(__file__))
CAP = os.path.join(AQUI, '..', '..', 'capturas')
sys.path.insert(0, AQUI)
import terminal_png  # noqa: E402

os.makedirs(TMP, exist_ok=True)
if IMPRIMIR:   # terminales claras: no gastan tinta
    terminal_png.FONDO, terminal_png.BARRA = (248, 248, 248), (225, 229, 236)
    terminal_png.COLORES.update(normal=(40, 40, 40), cmd=(110, 80, 0), ok=(15, 110, 45), mal=(180, 30, 30),
                                gris=(110, 110, 110), titulo=(26, 77, 143))

AZUL, FTE, MONO = '1A4D8F', 'Arial', 'Consolas'
ANCHO = 500.0 if IMPRIMIR else 242.0   # puntos útiles
doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Pt(283), Pt(505)
s.left_margin = s.right_margin = Pt(20)
s.top_margin, s.bottom_margin = Pt(20), Pt(24)
if IMPRIMIR:
    s.page_width, s.page_height = Pt(612), Pt(792)
    s.left_margin = s.right_margin = Pt(56)
    s.top_margin, s.bottom_margin = Pt(46), Pt(48)
BASE = 10.5 if IMPRIMIR else 8.5
TAB = 9.5 if IMPRIMIR else BASE - .9
s.header_distance = Pt(8)
s.footer_distance = Pt(26 if IMPRIMIR else 8)
doc.core_properties.title = 'Defensa del Sprint 4 — guía de estudio'
doc.core_properties.author = 'Grupo 15'


def estilo(nombre, tam, color='222222', negrita=False, antes=0, desp=4, sig=False):
    st = doc.styles[nombre]
    st.font.name, st.font.size, st.font.bold = FTE, Pt(tam), negrita
    st.font.italic = False
    st.font.color.rgb = RGBColor.from_string(color)
    rf = st.element.get_or_add_rPr().get_or_add_rFonts()
    for a in list(rf.attrib):
        if 'Theme' in a:
            del rf.attrib[a]
    for a in ('ascii', 'hAnsi', 'cs', 'eastAsia'):
        rf.set(qn('w:' + a), FTE)
    pf = st.paragraph_format
    pf.space_before, pf.space_after, pf.keep_with_next = Pt(antes), Pt(desp), sig
    pf.line_spacing = 1.12


estilo('Normal', BASE, desp=5 if IMPRIMIR else 4)
estilo('Title', 22 if IMPRIMIR else 15, AZUL, True, 0, 3)
estilo('Heading 1', 17 if IMPRIMIR else 12, AZUL, True, 20 if IMPRIMIR else 0, 7 if IMPRIMIR else 5, True)
estilo('Heading 2', 12.5 if IMPRIMIR else 10, AZUL, True, 10 if IMPRIMIR else 8, 5 if IMPRIMIR else 3, True)
estilo('Heading 3', BASE + .3, '222222', True, 6, 2, True)
estilo('List Bullet', BASE, desp=3 if IMPRIMIR else 2)
doc.styles['List Bullet'].paragraph_format.left_indent = Pt(12)
doc.styles['List Bullet'].paragraph_format.first_line_indent = Pt(-10)
for lang in doc.styles.element.iter(qn('w:lang')):
    lang.set(qn('w:val'), 'es-BO')
pp = doc.styles['Title'].element.find(qn('w:pPr'))
b = pp.find(qn('w:pBdr'))
if b is not None:
    pp.remove(b)


def rico(p, txt, tam=None):
    """Texto con **negrita** y `código`."""
    for parte in re.split(r'(\*\*.+?\*\*|`.+?`)', txt):
        if not parte:
            continue
        if parte.startswith('**'):
            r = p.add_run(parte[2:-2].replace('`', ''))
            r.bold = True
        elif parte.startswith('`'):
            r = p.add_run(parte[1:-1])
            r.font.name = MONO
            r.font.size = Pt((tam or BASE) - .5)
            continue
        else:
            r = p.add_run(parte)
        if tam:
            r.font.size = Pt(tam)
    return p


def borde(p, lado, color, sz=6, esp=2):
    ppr = p._p.get_or_add_pPr()
    bd = OxmlElement('w:pBdr')
    e = OxmlElement('w:' + lado)
    for k, v in (('val', 'single'), ('sz', sz), ('space', esp), ('color', color)):
        e.set(qn('w:' + k), str(v))
    bd.append(e)
    ref = next((h for h in ppr if h.tag in (qn('w:shd'), qn('w:spacing'), qn('w:ind'), qn('w:jc'))), None)
    if ref is not None:
        ref.addprevious(bd)
    else:
        ppr.append(bd)


def h1(t):
    p = doc.add_heading(t, 1)
    p.paragraph_format.page_break_before = not IMPRIMIR or t[:2] == '1.'
    borde(p, 'bottom', 'C9D3E6')


def h2(t):
    doc.add_heading(t, 2)


def h3(t):
    doc.add_heading(t, 3)


def P(t, tam=None):
    return rico(doc.add_paragraph(), t, tam)


def B(*ts):
    for t in ts:
        rico(doc.add_paragraph(style='List Bullet'), t)


def N(*ts):
    """Lista numerada con su propia cuenta (reinicia en 1)."""
    for i, t in enumerate(ts, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Pt(14), Pt(-14)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.tab_stops.add_tab_stop(Pt(14))
        rico(p, f'**{i}.**\t{t}')


def sombra(celda, color):
    sh = OxmlElement('w:shd')
    for k, v in (('val', 'clear'), ('color', 'auto'), ('fill', color)):
        sh.set(qn('w:' + k), v)
    celda._tc.get_or_add_tcPr().append(sh)


def bordes_tabla(t, lados, color):
    """lados: {lado: grosor}. Deja también los márgenes de celda."""
    tp = t._tbl.tblPr
    bd = OxmlElement('w:tblBorders')
    for lado in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement('w:' + lado)
        vals = (('val', 'single'), ('sz', lados[lado]), ('space', 0), ('color', color)) if lado in lados \
            else (('val', 'nil'),)
        for k, v in vals:
            e.set(qn('w:' + k), str(v))
        bd.append(e)
    ind = OxmlElement('w:tblInd')
    ind.set(qn('w:w'), '100' if IMPRIMIR else '70')
    ind.set(qn('w:type'), 'dxa')
    mar = OxmlElement('w:tblCellMar')
    for lado, v in (('top', 35 if IMPRIMIR else 30), ('left', 100 if IMPRIMIR else 70),
                    ('bottom', 35 if IMPRIMIR else 30), ('right', 100 if IMPRIMIR else 70)):
        e = OxmlElement('w:' + lado)
        e.set(qn('w:w'), str(v))
        e.set(qn('w:type'), 'dxa')
        mar.append(e)
    look = tp.find(qn('w:tblLook'))
    lay = tp.find(qn('w:tblLayout'))
    if look is not None:
        ref = lay if lay is not None else look
        ref.addprevious(ind)
        ref.addprevious(bd)
        look.addprevious(mar)
    else:
        tp.append(bd)
        tp.append(mar)


def espacio(pt=7 if IMPRIMIR else 5):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(pt)


def no_partir(fila):
    fila._tr.get_or_add_trPr().insert(0, OxmlElement('w:cantSplit'))


def T(cab, filas, anchos):
    """Tabla de datos; anchos en % del útil."""
    if IMPRIMIR and len(filas) >= 12 and cab[0] not in ('Qué', 'Dónde') and all(len(x) < 42 for f in filas for x in f):
        # Lista larga y angosta: dos bloques lado a lado.
        m = (len(filas) + 1) // 2
        vacia = ('',) * len(cab)
        filas = [tuple(filas[i]) + (tuple(filas[i + m]) if i + m < len(filas) else vacia) for i in range(m)]
        cab, anchos = tuple(cab) * 2, tuple(a / 2 for a in anchos) * 2
    t = doc.add_table(1, len(cab))
    t.autofit = False
    bordes_tabla(t, dict.fromkeys(('top', 'left', 'bottom', 'right', 'insideH', 'insideV'), 4), 'BFC8D9')
    ws = [Pt(ANCHO * a / 100) for a in anchos]
    for c, v in zip(t.rows[0].cells, cab):
        sombra(c, 'E6ECF6')
        rico(c.paragraphs[0], f'**{v}**' if v else '', TAB)
    for f in filas:
        for c, v in zip(t.add_row().cells, f):
            rico(c.paragraphs[0], v, TAB)
    for i, r in enumerate(t.rows):
        no_partir(r)
        if i == 0:
            r._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for c, w in zip(r.cells, ws):
            c.width = w
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(0)
                if i < min(2, len(t.rows) - 1):
                    p.paragraph_format.keep_with_next = True
    for gc, w in zip(t._tbl.tblGrid.findall(qn('w:gridCol')), ws):
        gc.set(qn('w:w'), str(int(w.pt * 20)))
    espacio()


def una_celda(fondo, barra):
    t = doc.add_table(1, 1)
    t.autofit = False
    bordes_tabla(t, {'left': 18}, barra)
    c = t.rows[0].cells[0]
    c.width = Pt(ANCHO)
    sombra(c, fondo)
    t._tbl.tblGrid.find(qn('w:gridCol')).set(qn('w:w'), str(int(ANCHO * 20)))
    no_partir(t.rows[0])
    return c


def caja(txt, fondo='FFF4DC', barra='E0A800'):
    c = una_celda(fondo, barra)
    for i, linea in enumerate(txt if isinstance(txt, list) else [txt]):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        rico(p, linea, BASE - .2)
    espacio()


def idea(t):
    caja(t)


def decir(t):
    caja('**Puedes decir:** ' + t, 'E6F5EC', '2E9E5B')


def ojo(t):
    caja('**Ojo:** ' + t, 'FDE9E7', 'D0453A')


def codigo(txt):
    c = una_celda('F0F4FA', AZUL)
    for i, linea in enumerate(txt.strip('\n').split('\n')):
        p = c.paragraphs[0] if i == 0 else c.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(linea)
        r.font.name = MONO
        r.font.size = Pt(9.5 if IMPRIMIR else 7.2)
    espacio()


cola = []


def poner(p, ruta, pie, ancho, alto):
    w, h = Image.open(ruta).size
    ancho = min(ancho, alto * w / h)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(2)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(ruta, width=Pt(ancho))
    p._p.find('.//' + qn('wp:docPr')).set('descr', pie)


def pie_de(q, pie):
    q.alignment = WD_ALIGN_PARAGRAPH.CENTER
    q.paragraph_format.space_after = Pt(8 if IMPRIMIR else 6)
    r = q.add_run(pie)
    r.font.size = Pt(9 if IMPRIMIR else 7)
    r.italic = True
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def vaciar():
    """Dibuja las imágenes pendientes: de a dos, lado a lado, y la que sobra, sola."""
    pend = cola[:]
    cola.clear()
    while pend:
        def muy_ancha(x):
            w, h = Image.open(x[0]).size
            return w > 3.5 * h
        n = 2 if len(pend) > 1 and not muy_ancha(pend[0]) and not muy_ancha(pend[1]) else 1
        grupo, pend = pend[:n], pend[n:]
        if n == 1:
            ruta, pie, ancho = grupo[0]
            alta = Image.open(ruta).size
            previos = []
            x = doc.element.body.sectPr.getprevious() if doc.element.body.sectPr is not None else doc.element.body[-1]
            while x is not None and x.tag == qn('w:p'):
                est = x.find(qn('w:pPr') + '/' + qn('w:pStyle'))
                titulo = est is not None and est.get(qn('w:val')).startswith(('Heading', 'Title'))
                centrado = x.find(qn('w:pPr') + '/' + qn('w:jc')) is not None
                if titulo or centrado or x.find('.//' + qn('w:drawing')) is not None or not ''.join(x.itertext()).strip():
                    break
                previos.insert(0, x)
                x = x.getprevious()
            if previos and alta[1] > alta[0] * .42 and 'term' not in os.path.basename(ruta):
                t = agregar_tabla(1, 2)
                t.autofit = False
                bordes_tabla(t, {}, 'FFFFFF')
                alto_max = 185
                w = min(230, ancho, alto_max * alta[0] / alta[1])
                der = max(w + 16, 150)
                for c, g, v in zip(t.rows[0].cells, t._tbl.tblGrid.findall(qn('w:gridCol')), (ANCHO - der, der)):
                    c.width = Pt(v)
                    g.set(qn('w:w'), str(int(v * 20)))
                izq, dc = t.rows[0].cells
                hueco = izq.paragraphs[0]._p
                for x in previos:
                    hueco.addprevious(x)
                izq._tc.remove(hueco)
                poner(dc.paragraphs[0], ruta, pie, w, alto_max)
                pie_de(dc.add_paragraph(), pie)
                no_partir(t.rows[0])
                sep = agregar_parrafo()
                sep.paragraph_format.space_after = Pt(0)
                sep.paragraph_format.line_spacing = Pt(4)
                continue
            poner(agregar_parrafo(), ruta, pie, ancho, 260)
            pie_de(agregar_parrafo(), pie)
            continue
        t = agregar_tabla(2, 2)
        t.autofit = False
        bordes_tabla(t, {}, 'FFFFFF')
        for i, (ruta, pie, ancho) in enumerate(grupo):
            for f in (0, 1):
                t.cell(f, i).width = Pt(ANCHO / 2)
            poner(t.cell(0, i).paragraphs[0], ruta, pie, min(ancho, ANCHO / 2 - 14), 200)
            pie_de(t.cell(1, i).paragraphs[0], pie)
        for gc in t._tbl.tblGrid.findall(qn('w:gridCol')):
            gc.set(qn('w:w'), str(int(ANCHO * 10)))
        for fila in t.rows:
            no_partir(fila)
        sep = agregar_parrafo()
        sep.paragraph_format.space_after = Pt(0)
        sep.paragraph_format.line_spacing = Pt(6)


agregar_parrafo, agregar_titulo, agregar_tabla = doc.add_paragraph, doc.add_heading, doc.add_table


def con_vaciado(f):
    def g(*a, **k):
        if cola:
            vaciar()
        return f(*a, **k)
    return g


if IMPRIMIR:
    doc.add_paragraph, doc.add_table = con_vaciado(agregar_parrafo), con_vaciado(agregar_tabla)
    doc.add_heading = lambda txt, n: doc.add_paragraph(txt, style=f'Heading {n}')


def img(ruta, pie, ancho=ANCHO):
    if IMPRIMIR:
        cola.append((ruta, pie, ancho))
        return
    poner(doc.add_paragraph(), ruta, pie, ancho, 330)
    pie_de(doc.add_paragraph(), pie)


nimg = [0]


def nueva(prefijo):
    nimg[0] += 1
    return os.path.join(TMP, f'{prefijo}{nimg[0]}.png')


def cap(patron, pie, corte=None, ancho=400 if IMPRIMIR else ANCHO):
    """Captura recortada; corte = (x0, y0, x1, y1) en fracción."""
    im = Image.open(glob.glob(os.path.join(CAP, patron))[0]).convert('RGB')
    if corte:
        w, h = im.size
        # Varios cortes: se unen en fila (modo 'h') o uno debajo del otro ('v').
        modo, cortes = corte if isinstance(corte[0], str) else ('h', [corte])
        ps = [im.crop((int(a * w), int(b * h), int(c * w), int(e * h))) for a, b, c, e in cortes]
        if modo == 'h':
            im = Image.new('RGB', (sum(x.width for x in ps), max(x.height for x in ps)), 'white')
        else:
            im = Image.new('RGB', (max(x.width for x in ps), sum(x.height for x in ps)), 'white')
        pos = 0
        for x in ps:
            im.paste(x, (pos, 0) if modo == 'h' else (0, pos))
            pos += x.width if modo == 'h' else x.height
    if IMPRIMIR and im.height > im.width * .75:
        ancho = min(ancho, 250)
    elif IMPRIMIR:
        ancho = max(ancho, 300)
    if im.width > 900:
        im = im.resize((900, int(im.height * 900 / im.width)), Image.LANCZOS)
    m = Image.new('RGB', (im.width + 4, im.height + 4), (190, 198, 212))
    m.paste(im, (2, 2))
    r = nueva('cap')
    m.save(r)
    img(r, pie, ancho)


def fuente(t, negrita=False):
    return ImageFont.truetype(r'C:\Windows\Fonts\arial' + ('bd' if negrita else '') + '.ttf', t)


def partir(d, txt, f, w):
    out, linea = [], ''
    for pal in txt.split():
        if d.textlength((linea + ' ' + pal).strip(), font=f) > w:
            out.append(linea)
            linea = pal
        else:
            linea = (linea + ' ' + pal).strip()
    return out + [linea]


COL = {'a': ('E6F0FB', '2F6FB7'), 'v': ('E6F5EC', '2E9E5B'), 'r': ('FDE9E7', 'D0453A'),
       'n': ('FFF4DC', 'C99700'), 'g': ('F1F1F4', '888888')}


def flujo(pasos, pie):
    """Flujo [(color, título, detalle, salida o None)]: vertical en celular, horizontal al imprimir."""
    if IMPRIMIR:
        n, W, sep = len(pasos), 2000, 46
        w = (W - 20 - sep * (n - 1)) // n
        tmp = ImageDraw.Draw(Image.new('RGB', (10, 10)))
        ft, fd = fuente(35, True), fuente(32)
        tx = [(partir(tmp, t, ft, w - 28), partir(tmp, d_, fd, w - 28) if d_ else [],
               partir(tmp, lat, fd, w - 8) if lat else []) for _, t, d_, lat in pasos]
        h = 30 + max(len(a) * 42 + len(b) * 38 for a, b, _ in tx)
        extra = max((len(c) for *_, c in tx), default=0)
        im = Image.new('RGB', (W, h + 20 + (60 + extra * 38 if extra else 0)), 'white')
        d = ImageDraw.Draw(im)
        for i, ((c, *_), (a, b, l)) in enumerate(zip(pasos, tx)):
            x = 10 + i * (w + sep)
            fo, bo = ('#' + v for v in COL[c])
            d.rounded_rectangle([x, 8, x + w, 8 + h], 16, fill=fo, outline=bo, width=4)
            y = 22
            for v in a:
                d.text((x + 14, y), v, font=ft, fill='#222222')
                y += 42
            for v in b:
                d.text((x + 14, y), v, font=fd, fill='#333333')
                y += 38
            if i < n - 1:
                ym = 8 + h // 2
                d.line([x + w + 2, ym, x + w + 26, ym], fill='#555555', width=5)
                d.polygon([(x + w + 24, ym - 13), (x + w + 24, ym + 13), (x + w + sep - 2, ym)], fill='#555555')
            if l:
                xm = x + w // 2
                d.line([xm, 8 + h, xm, h + 36], fill='#D0453A', width=5)
                d.polygon([(xm - 13, h + 34), (xm + 13, h + 34), (xm, h + 54)], fill='#D0453A')
                for j, v in enumerate(l):
                    d.text((xm - d.textlength(v, font=fd) / 2, h + 58 + j * 38), v, font=fd, fill='#B03028')
        vaciar()
        r = nueva('flujo')
        im.save(r)
        poner(doc.add_paragraph(), r, pie, ANCHO, 300)
        pie_de(doc.add_paragraph(), pie)
        return
    tmp = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    ft, fd = fuente(38, True), fuente(33)
    cajas, y = [], 10
    for c, t, det, lat in pasos:
        wc = 600 if lat else 940
        lt = partir(tmp, t, ft, wc - 40)
        ld = partir(tmp, det, fd, wc - 40) if det else []
        ll = partir(tmp, lat, fd, 262) if lat else []
        h = max(28 + len(lt) * 46 + len(ld) * 40, 28 + len(ll) * 40)
        cajas.append((c, lt, ld, ll, y, h, wc))
        y += h + 52
    im = Image.new('RGB', (1000, y - 40), 'white')
    d = ImageDraw.Draw(im)
    for i, (c, lt, ld, ll, y0, h, wc) in enumerate(cajas):
        fondo, linea = ('#' + x for x in COL[c])
        d.rounded_rectangle([30, y0, 30 + wc, y0 + h], 16, fill=fondo, outline=linea, width=4)
        yy = y0 + 13
        for x in lt:
            d.text((50, yy), x, font=ft, fill='#222222')
            yy += 46
        for x in ld:
            d.text((50, yy), x, font=fd, fill='#333333')
            yy += 40
        if ll:
            ym = y0 + h // 2
            d.line([630, ym, 690, ym], fill='#D0453A', width=5)
            d.polygon([(690, ym - 13), (712, ym), (690, ym + 13)], fill='#D0453A')
            yy = ym - len(ll) * 20
            for x in ll:
                d.text((722, yy), x, font=fd, fill='#B03028')
                yy += 40
        if i < len(cajas) - 1:
            yb = y0 + h
            d.line([330, yb, 330, yb + 36], fill='#555555', width=5)
            d.polygon([(317, yb + 30), (343, yb + 30), (330, yb + 51)], fill='#555555')
    r = nueva('flujo')
    im.save(r)
    img(r, pie, 300 if IMPRIMIR else ANCHO)


def leer(f):
    crudo = open(os.path.join(EJEC, f), 'rb').read()
    try:
        return crudo.decode('utf-8')
    except UnicodeDecodeError:
        return crudo.decode('cp1252')


def terminal(titulo, lineas, pie):
    terminal_png.ANCHO_COLS = 92 if IMPRIMIR else 50
    r = nueva('term')
    terminal_png.dibujar(titulo, lineas, r)
    img(r, pie, 440 if IMPRIMIR else ANCHO)


def total(arch):
    return next(x for x in reversed(leer(arch + '.txt').splitlines()) if ' passed' in x)


def pyt(arch, nombres, pie, tope=4):
    """Extracto real de pytest -v."""
    lineas = leer(arch + '.txt').splitlines()
    out = [f'$ python -m pytest tests/{arch}.py -v', '…']
    for n in nombres:
        hits = [x for x in lineas if re.search(rf'::{n}(\[| )', x) and 'PASSED' in x]
        if not hits:
            raise SystemExit('No está: ' + n)
        out += hits[:tope]
        if len(hits) > tope:
            out.append(f'… (y {len(hits) - tope} casos más de esta función, todos PASSED)')
    terminal('pytest', out + ['…', total(arch).strip('= ')], pie)


def QA(q, a):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(7 if IMPRIMIR else 5), Pt(2 if IMPRIMIR else 1)
    p.paragraph_format.keep_with_next = True
    r = p.add_run('P. ' + q)
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(AZUL)
    P('**R.** ' + a)


fp = s.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
for tipo in ('begin', None, 'end'):
    r = fp.add_run()
    r.font.size = Pt(7)
    if tipo:
        e = OxmlElement('w:fldChar')
        e.set(qn('w:fldCharType'), tipo)
    else:
        e = OxmlElement('w:instrText')
        e.text = 'PAGE'
    r._r.append(e)

exec(open(os.path.join(AQUI, 'guia_sprint4_contenido.py'), encoding='utf-8').read())
vaciar()
zoom = doc.settings.element.find(qn('w:zoom'))
if zoom is not None:
    zoom.set(qn('w:percent'), '100')
doc.save(SAL)
print('OK', SAL)
