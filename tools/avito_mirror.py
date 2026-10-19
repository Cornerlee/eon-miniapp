# Копирует фиды Авито с сервера магазина на GitHub Pages: серверы Авито не достают до supabase.co,
# а до github.io достают. Фото с supabase.co тоже переносятся сюда. Запускается GitHub Actions раз в час.
import hashlib
import os
import re
import time
import urllib.request

API = "https://azezshsjnnpjrscstwcb.supabase.co/functions/v1/eon"
SITE = "https://cornerlee.github.io/eon-miniapp/"
OUT = "avito"
WINTER = {"Зимние куртки и пуховики", "Дублёнки", "Шубы", "Дублёнки и шубы", "Парки", "Угги, валенки, дутики"}
DEMI = {"Демисезонные куртки", "Бомберы", "Джемперы, свитеры, кардиганы"}


def get(url, tries=4):
    req = urllib.request.Request(url, headers={"User-Agent": "ep-avito-mirror"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read(), r.headers.get("content-type", "")
        except OSError:
            if k == tries - 1:
                raise
            time.sleep(3)


def mirror_image(url):
    if url.startswith(SITE):
        return url
    name = hashlib.sha1(url.encode()).hexdigest()[:16]
    for ext in (".jpg", ".png"):
        if os.path.exists(f"{OUT}/img/{name}{ext}"):
            return f"{SITE}{OUT}/img/{name}{ext}"
    data, ctype = get(url.replace("&amp;", "&"))
    ext = ".png" if "png" in ctype else ".jpg"
    with open(f"{OUT}/img/{name}{ext}", "wb") as f:
        f.write(data)
    return f"{SITE}{OUT}/img/{name}{ext}"


def season(ad):
    kind = (re.search(r"<ApparelType>(.*?)</ApparelType>", ad) or re.search(r"<Apparel>(.*?)</Apparel>", ad) or [None, ""])[1]
    title = (re.search(r"<Title>(.*?)</Title>", ad) or [None, ""])[1].lower()
    if kind in WINTER or re.search(r"утепл|начёс|начес|тёпл|тепл", title):
        return "Зима"
    if kind in DEMI:
        return "Демисезон"
    return "Любой"


def fix_ad(m):
    ad = m.group(0)
    ad = re.sub(r'<Image url="([^"]+)"/>', lambda i: f'<Image url="{mirror_image(i.group(1))}"/>', ad)
    if "<Season>" not in ad:
        ad = ad.replace("<Title>", f"<Season><Option>{season(ad)}</Option></Season><Title>", 1)
    return ad


os.makedirs(f"{OUT}/img", exist_ok=True)
for n in (1, 2, 3):
    xml = get(f"{API}?avito={n}")[0].decode("utf-8")
    if not xml.lstrip().startswith("<?xml"):
        raise SystemExit(f"feed {n}: unexpected response")
    xml = re.sub(r"<Ad>.*?</Ad>", fix_ad, xml, flags=re.S)
    with open(f"{OUT}/feed-{n}.xml", "w", encoding="utf-8", newline="\n") as f:
        f.write(xml)
    print(f"feed {n}: {xml.count('<Ad>')} ads")
