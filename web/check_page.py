# Прогон страницы в headless Firefox: ошибки, скриншот превью, скачанный PDF. Первый прогон — русский интерфейс.
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pocherk"
PAGE = Path(__file__).resolve().with_name("index.html").as_uri()  # язык: ?lang=ru / ?lang=en
with sync_playwright() as p:
    br = p.firefox.launch()
    pg = br.new_page(viewport={"width": 1300, "height": 1000}, accept_downloads=True)
    errors = []
    pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.goto(PAGE + "?lang=ru")
    pg.wait_for_timeout(1500)
    print("status:", pg.inner_text("#status"))
    pg.screenshot(path=f"{OUT}-page.png")
    with pg.expect_download(timeout=30000) as dl:
        pg.click("#pdf")
    dl.value.save_as(f"{OUT}.pdf")
    pg.wait_for_timeout(300)
    print("status after:", pg.inner_text("#status").splitlines()[-1])
    print("errors:", errors or "нет")
    br.close()

# Второй прогон: английский интерфейс, длинный текст, небрежность 1, эмодзи/латиница/таб; шрифт — второй аргумент (shantell).
with sync_playwright() as p:
    br = p.firefox.launch()
    pg = br.new_page(viewport={"width": 1300, "height": 1000}, accept_downloads=True)
    errors = []
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    pg.goto(PAGE + "?lang=en")
    long = ("Длинный абзац с латиницей (Hello, world!), эмодзи 😀, знаком € и\tтабом. " * 12 + "\n") * 8 \
        + "Слово_без_пробелов_" * 12
    pg.fill("#text", long)
    pg.select_option("#font", sys.argv[2] if len(sys.argv) > 2 else "shantell")
    pg.eval_on_selector("#mess", "el => { el.value = 1; el.dispatchEvent(new Event('input')); }")
    pg.wait_for_timeout(1500)
    print("run2 status:", pg.inner_text("#status").splitlines()[0])
    pg.screenshot(path=f"{OUT}-page2.png")
    with pg.expect_download(timeout=60000) as dl:
        pg.click("#pdf")
    dl.value.save_as(f"{OUT}-2.pdf")
    pg.wait_for_timeout(300)
    print("run2 after:", pg.inner_text("#status").splitlines()[-1], "| errors:", errors or "нет")
    br.close()
