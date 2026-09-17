# Готовит шрифты для web/: статический инстанс + карта «буква → id глифов-вариантов» -> web/fonts.js.
# Варианты — все глифы, достижимые из базового заменами в указанных фичах GSUB (вместе с вложенными
# lookup'ами контекстных правил). Фичи у каждого шрифта свои: у Caveat формы лежат в ss01/ss02,
# у Shantell Sans — в rlig, у Playpen Sans — в calt. locl не берём: сербские и болгарские формы —
# другие буквы, не варианты.
# Исходники качаются из google/fonts в src/, если их там нет. Нужен fonttools.
import base64, io, json, os, urllib.request
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "web", "fonts.js")
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = [
    dict(key="caveat", title="Caveat (3 формы букв)", file="Caveat[wght].ttf", url=GF + "caveat/Caveat%5Bwght%5D.ttf",
         axes={"wght": 400}, features=["ss01", "ss02"]),
    dict(key="shantell", title="Shantell Sans, informal (4 формы)", file="ShantellSans[BNCE,INFM,SPAC,wght].ttf",
         url=GF + "shantellsans/ShantellSans%5BBNCE%2CINFM%2CSPAC%2Cwght%5D.ttf",
         axes={"wght": 400, "INFM": 1, "BNCE": 0, "SPAC": 0}, features=["rlig"]),
    dict(key="playpen", title="Playpen Sans (7 форм)", file="PlaypenSans[wght].ttf", url=GF + "playpensans/PlaypenSans%5Bwght%5D.ttf",
         axes={"wght": 400}, features=["calt"]),
]
LICENSE = "SIL Open Font License 1.1 (google/fonts)"


def substitutions(f, features):
    """glyph -> множество глифов, на которые его меняют одиночные/альтернативные замены в features."""
    edges = {}
    if "GSUB" not in f:
        return edges
    table = f["GSUB"].table
    lookups = table.LookupList.Lookup

    def walk(i, seen):
        if i in seen:
            return
        seen.add(i)
        lk = lookups[i]
        for st in lk.SubTable:
            t = st.ExtSubTable if lk.LookupType == 7 else st
            kind = t.LookupType if lk.LookupType == 7 else lk.LookupType
            if kind == 1:
                for a, b in t.mapping.items():
                    edges.setdefault(a, set()).add(b)
            elif kind == 3:
                for a, bs in t.alternates.items():
                    edges.setdefault(a, set()).update(bs)
            elif kind in (5, 6):  # контекстные правила: идём во вложенные lookup'ы
                records = list(getattr(t, "SubstLookupRecord", None) or [])
                for name in ("SubRuleSet", "SubClassSet", "ChainSubRuleSet", "ChainSubClassSet"):
                    for rs in filter(None, getattr(t, name, None) or []):
                        for rule_name in ("SubRule", "SubClassRule", "ChainSubRule", "ChainSubClassRule"):
                            for rule in getattr(rs, rule_name, None) or []:
                                records += rule.SubstLookupRecord
                for r in records:
                    walk(r.LookupListIndex, seen)

    for fr in table.FeatureList.FeatureRecord:
        if fr.FeatureTag in features:
            for i in fr.Feature.LookupListIndex:
                walk(i, set())
    return edges


def build(spec):
    path = os.path.join(HERE, "src", spec["file"])
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        urllib.request.urlretrieve(spec["url"], path)
    f = TTFont(path)
    if "fvar" in f:
        f = instantiateVariableFont(f, spec["axes"])
    gid = {g: i for i, g in enumerate(f.getGlyphOrder())}
    edges = substitutions(f, spec["features"])
    variants = {}
    for cp, g in f.getBestCmap().items():
        forms, stack = {g}, [g]
        while stack:
            for b in edges.get(stack.pop(), ()):
                if b not in forms:
                    forms.add(b)
                    stack.append(b)
        if len(forms) > 1:
            variants[chr(cp)] = [gid[g]] + sorted(gid[b] for b in forms - {g})
    f.recalcTimestamp = False  # иначе head.modified = «сейчас» и fonts.js меняется при каждой сборке
    buf = io.BytesIO()
    f.save(buf)
    data = buf.getvalue()
    print(f"{spec['key']}: {len(data) // 1024} КБ, букв с вариантами: {len(variants)}, "
          f"форм у «б»: {len(variants.get('б', [0]))}")
    return dict(title=spec["title"], license=LICENSE, b64=base64.b64encode(data).decode(), variants=variants)


if __name__ == "__main__":
    fonts = {s["key"]: build(s) for s in FONTS}
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("// Сгенерировано fonts/build_web_fonts.py, руками не править.\n")
        fh.write("window.FONTS = " + json.dumps(fonts, ensure_ascii=False) + ";\n")
    print("->", os.path.normpath(OUT), os.path.getsize(OUT) // 1024, "КБ")
