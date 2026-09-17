# Кириллица и формы букв у шрифтов в папке: python font_survey.py <папка с .ttf>
# Форма = глиф, достижимый из базового заменами в calt/rlig/rand/salt/ssNN/cvNN (с вложенными
# lookup'ами контекстных правил). Смотреть глазами всё равно нужно: у рукописных шрифтов с соединениями
# в calt лежат формы входа/выхода штриха, у Pacifico — конечные формы; случайно их выбирать нельзя.
import glob, os, sys
from fontTools.ttLib import TTFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_web_fonts import substitutions  # noqa: E402

LOWER = [chr(c) for c in range(0x430, 0x450)] + ["ё"]


def feature_tags(f):
    if "GSUB" not in f:
        return []
    tags = {fr.FeatureTag for fr in f["GSUB"].table.FeatureList.FeatureRecord}
    return sorted(t for t in tags if t in ("calt", "rlig", "rand", "salt") or t[:2] in ("ss", "cv"))


for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.ttf"))):
    f = TTFont(path)
    cmap = f.getBestCmap()
    tags = feature_tags(f)
    edges = substitutions(f, tags)
    counts = []
    for ch in LOWER:
        if ord(ch) not in cmap:
            continue
        forms, stack = {cmap[ord(ch)]}, [cmap[ord(ch)]]
        while stack:
            for b in edges.get(stack.pop(), ()):
                if b not in forms:
                    forms.add(b)
                    stack.append(b)
        counts.append(len(forms))
    multi = sum(n > 1 for n in counts)
    print(f"{os.path.basename(path):42s} строчная кириллица {len(counts)}/33, с формами {multi}, "
          f"форм макс {max(counts, default=0)}; фичи {tags}")
