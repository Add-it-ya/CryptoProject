"""Small helper layer over python-pptx: themed text boxes/cards, native entrance animations (raw
PresentationML timing XML), slide transitions and speaker notes."""
import itertools

from lxml import etree
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

# ------------------------------------------------------------------ palette / fonts
def rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


C = {
    "bg": "070D1C",
    "card": "0E1A34",
    "card2": "13223F",
    "line": "24365C",
    "text": "E8EEF7",
    "muted": "9AABC8",
    "cyan": "22D3EE",
    "green": "34D399",
    "red": "F87171",
    "amber": "FBBF24",
    "violet": "A78BFA",
    "white": "FFFFFF",
    "ink": "081022",
}
HEAD = "Segoe UI Semibold"
BODY = "Segoe UI"
MONO = "Consolas"


# ------------------------------------------------------------------ primitives
def _set_alpha(fill_fore_color_xml_parent, alpha):
    """alpha 0..1 on an <a:solidFill><a:srgbClr/></a:solidFill>"""
    clr = fill_fore_color_xml_parent.find(qn("a:srgbClr"))
    if clr is not None:
        for a in clr.findall(qn("a:alpha")):
            clr.remove(a)
        el = etree.SubElement(clr, qn("a:alpha"))
        el.set("val", str(int(alpha * 100000)))


def box(slide, x, y, w, h, fill=None, line=None, radius=0.08, alpha=None, line_w=1.0, shape=MSO_SHAPE.ROUNDED_RECTANGLE, dash=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill:
        s.fill.solid()
        s.fill.fore_color.rgb = rgb(C.get(fill, fill))
        if alpha is not None:
            _set_alpha(s.fill._xPr.find(qn("a:solidFill")), alpha)
    else:
        s.fill.background()
    if line:
        s.line.color.rgb = rgb(C.get(line, line))
        s.line.width = Pt(line_w)
        if dash:
            s.line.dash_style = dash
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = Inches(0.04)
    return s


def text(slide, x, y, w, h, paras, size=16, color="text", font=BODY, bold=False, align="l", anchor="t", spacing=1.08, margin=0.0, after=0, shape=None):
    """paras: str | list[str | list[(text, opts)]]  opts: size,color,font,bold,italic"""
    if shape is None:
        shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = tf.margin_right = Inches(margin)
    tf.margin_top = tf.margin_bottom = Inches(margin / 2)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, str):
        paras = [paras]
    first = True
    for p in paras:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        para.line_spacing = spacing
        if after:
            para.space_after = Pt(after)
        runs = [(p, {})] if isinstance(p, str) else p
        for t, o in runs:
            r = para.add_run()
            r.text = t
            f = r.font
            f.size = Pt(o.get("size", size))
            f.name = o.get("font", font)
            f.bold = o.get("bold", bold)
            f.italic = o.get("italic", False)
            f.color.rgb = rgb(C.get(o.get("color", color), o.get("color", color)))
    return shape


def pic(slide, path, x, y, w=None, h=None):
    return slide.shapes.add_picture(path, Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)


def background(slide, path, prs):
    p = slide.shapes.add_picture(path, 0, 0, prs.slide_width, prs.slide_height)
    # move to back
    tree = slide.shapes._spTree
    tree.remove(p._element)
    tree.insert(2, p._element)
    return p


def group(slide, shapes):
    """Wrap already-created shapes into a group (so they animate together)."""
    g = slide.shapes.add_group_shape()
    for s in shapes:
        g._element.append(s._element)  # moves the element into the group
    # recompute group extents
    xs = [s.left for s in shapes]
    ys = [s.top for s in shapes]
    xe = [s.left + s.width for s in shapes]
    ye = [s.top + s.height for s in shapes]
    x0, y0, x1, y1 = min(xs), min(ys), max(xe), max(ye)
    grpSpPr = g._element.grpSpPr
    xfrm = grpSpPr.find(qn("a:xfrm"))
    if xfrm is None:
        xfrm = etree.SubElement(grpSpPr, qn("a:xfrm"))
    for tag, (a, b) in {"a:off": (x0, y0), "a:ext": (x1 - x0, y1 - y0), "a:chOff": (x0, y0), "a:chExt": (x1 - x0, y1 - y0)}.items():
        el = xfrm.find(qn(tag))
        if el is None:
            el = etree.SubElement(xfrm, qn(tag))
        if tag in ("a:off", "a:chOff"):
            el.set("x", str(a))
            el.set("y", str(b))
        else:
            el.set("cx", str(a))
            el.set("cy", str(b))
    return g


def notes(slide, txt):
    slide.notes_slide.notes_text_frame.text = txt


# ------------------------------------------------------------------ transitions
def transition(slide, kind="fade", speed="med"):
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    tr = etree.Element(qn("p:transition"))
    tr.set("spd", speed)
    if kind == "fade":
        etree.SubElement(tr, qn("p:fade"))
    elif kind == "push":
        e = etree.SubElement(tr, qn("p:push"))
        e.set("dir", "u")
    elif kind == "wipe":
        e = etree.SubElement(tr, qn("p:wipe"))
        e.set("dir", "r")
    elif kind == "cover":
        e = etree.SubElement(tr, qn("p:cover"))
        e.set("dir", "l")
    # transition must come right after clrMapOvr (before timing / extLst)
    clr = sld.find(qn("p:clrMapOvr"))
    clr.addnext(tr)


# ------------------------------------------------------------------ entrance animations
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

EFFECTS = {
    # name: (presetID, presetSubtype, filter or None, extra motion)
    "fade": (10, 0, "fade", None),
    "wipe_left": (22, 8, "wipe(left)", None),
    "wipe_down": (22, 1, "wipe(up)", None),  # reveals top -> bottom
    "rise": (42, 0, "fade", "rise"),
    "zoom": (53, 16, "fade", "zoom"),
}


class Animator:
    """Collects click groups for one slide and writes <p:timing>.
    group(trigger='click'|'auto'|'with', items=[(shape, effect, dur_ms)], stagger_ms)"""

    def __init__(self, slide):
        self.slide = slide
        self.groups = []

    def click(self, shapes, effect="fade", dur=500, stagger=120):
        self.groups.append(("click", [(s, effect, dur) for s in _flat(shapes)], stagger))

    def auto(self, shapes, effect="fade", dur=500, stagger=120):
        self.groups.append(("auto", [(s, effect, dur) for s in _flat(shapes)], stagger))

    def write(self):
        if not self.groups:
            return
        ids = itertools.count(3)
        clicks = []
        bld = []
        for trigger, items, stagger in self.groups:
            outer = next(ids)
            if trigger == "click":
                cond = '<p:cond delay="indefinite"/>'
            else:
                cond = '<p:cond delay="indefinite"/><p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond>'
            inner = []
            for k, (shape, eff, dur) in enumerate(items):
                pid, sub, flt, extra = EFFECTS[eff]
                spid = shape.shape_id
                node = ("clickEffect" if trigger == "click" else "afterEffect") if k == 0 else "withEffect"
                c1, c2, c3, c4, c5 = next(ids), next(ids), next(ids), next(ids), next(ids)
                motion = ""
                if extra == "rise":
                    motion = (
                        f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{c4}" dur="{dur}" decel="100000" fill="hold"/>'
                        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_y</p:attrName></p:attrNameLst></p:cBhvr>'
                        f'<p:tavLst><p:tav tm="0"><p:val><p:strVal val="#ppt_y+0.06"/></p:val></p:tav>'
                        f'<p:tav tm="100000"><p:val><p:strVal val="#ppt_y"/></p:val></p:tav></p:tavLst></p:anim>'
                    )
                elif extra == "zoom":
                    motion = (
                        f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{c4}" dur="{dur}" fill="hold"/>'
                        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_w</p:attrName></p:attrNameLst></p:cBhvr>'
                        f'<p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#ppt_w"/></p:val></p:tav></p:tavLst></p:anim>'
                        f'<p:anim calcmode="lin" valueType="num"><p:cBhvr><p:cTn id="{c5}" dur="{dur}" fill="hold"/>'
                        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>ppt_h</p:attrName></p:attrNameLst></p:cBhvr>'
                        f'<p:tavLst><p:tav tm="0"><p:val><p:fltVal val="0"/></p:val></p:tav><p:tav tm="100000"><p:val><p:strVal val="#ppt_h"/></p:val></p:tav></p:tavLst></p:anim>'
                    )
                inner.append(
                    f'<p:par><p:cTn id="{c1}" presetID="{pid}" presetClass="entr" presetSubtype="{sub}" fill="hold" grpId="0" nodeType="{node}">'
                    f'<p:stCondLst><p:cond delay="{k * stagger}"/></p:stCondLst><p:childTnLst>'
                    f'<p:set><p:cBhvr><p:cTn id="{c2}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                    f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                    f'<p:to><p:strVal val="visible"/></p:to></p:set>'
                    f'<p:animEffect transition="in" filter="{flt}"><p:cBhvr><p:cTn id="{c3}" dur="{dur}"/>'
                    f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                    f"{motion}</p:childTnLst></p:cTn></p:par>"
                )
                tag = etree.QName(shape._element).localname
                if tag == "sp":
                    bld.append(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')
                elif tag == "graphicFrame":
                    bld.append(f'<p:bldGraphic spid="{spid}" grpId="0"><p:bldAsOne/></p:bldGraphic>')
            clicks.append(
                f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst>{cond}</p:stCondLst><p:childTnLst>'
                f'<p:par><p:cTn id="{next(ids)}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                + "".join(inner)
                + "</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>"
            )
        xml = (
            f'<p:timing xmlns:p="{P_NS}" xmlns:a="{A_NS}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            + "".join(clicks)
            + '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
            "</p:childTnLst></p:cTn></p:par></p:tnLst>"
            + (f"<p:bldLst>{''.join(bld)}</p:bldLst>" if bld else "")
            + "</p:timing>"
        )
        el = etree.fromstring(xml)
        sld = self.slide._element
        for old in sld.findall(qn("p:timing")):
            sld.remove(old)
        ext = sld.find(qn("p:extLst"))
        if ext is not None:
            ext.addprevious(el)
        else:
            sld.append(el)


def _flat(x):
    if isinstance(x, (list, tuple)):
        out = []
        for i in x:
            out.extend(_flat(i))
        return out
    return [x]
