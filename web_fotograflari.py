# -*- coding: utf-8 -*-
"""Web kopyaları ve sayfa metaverisi. Python 3.9 + Pillow; sunucu gerektirmez."""
import hashlib
import html
import io
import json
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from xml.sax.saxutils import escape
from PIL import Image, ImageCms, ImageOps

SITE_URL = "https://selimbaltaci.github.io/"
SERILER = ["monochrom", "yanilsamalar", "secilmis-kareler", "yeni-kareler"]
UZANTILAR = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALBUM_ADLARI = ["Monochrom", "Yanılsamalar", "Seçilmiş Kareler", "Yeni Kareler"]


def json_oku(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def guvenli_yol(root, relative):
    path = (root / unquote(relative)).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("Site klasörü dışındaki fotoğraf yolu reddedildi.")
    return path


def dosya_kodu(relative):
    return hashlib.sha256(relative.encode("utf-8")).hexdigest()[:18]


def sirali_fotograflar(root, folder):
    """Yeni dosyalar önce; mevcut sıralama sıkıştırma/kopyalama ile değişmez."""
    base = root / "images" / folder
    if not base.is_dir():
        return []
    files = {p.relative_to(root).as_posix(): p for p in base.rglob("*")
             if p.is_file() and p.suffix.lower() in UZANTILAR
             and not any(part.startswith(".") for part in p.relative_to(base).parts)
             and not any(part in {"web", "site-media", "thumbs", "thumbnails"}
                         for part in p.relative_to(base).parts[:-1])}
    saved = json_oku(root / "foto-sirasi.json", {})
    old = [src for src in saved.get(folder, []) if src in files]
    new = sorted((src for src in files if src not in old),
                 key=lambda src: (-files[src].stat().st_mtime, src))
    return [(src, str(files[src])) for src in new + old]


def rgb_kopya(path):
    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original)
        profile = image.info.get("icc_profile")
        if profile:
            try:
                image = ImageCms.profileToProfile(image,
                    ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                    ImageCms.createProfile("sRGB"), outputMode="RGB")
            except (ImageCms.PyCMSError, OSError, ValueError):
                image = image.convert("RGB")
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image.copy()


def kaydet(image, target, edge, quality=82):
    resized = image.copy()
    resized.thumbnail((edge, edge), Image.Resampling.LANCZOS)
    target.parent.mkdir(parents=True, exist_ok=True)
    resized.save(target, "JPEG", quality=quality, optimize=True, progressive=True,
                 icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    return {"src": target.name, "width": resized.width, "height": resized.height,
            "bytes": target.stat().st_size}


def hazirla(root, archive=True):
    """Asılların yedeği site DIŞINDA; site içindeki dosyalar en fazla 2048px."""
    root = Path(root)
    cache = json_oku(root / "foto-web.json", {})
    sources = [p for p in (root / "images").rglob("*") if p.is_file()
               and p.suffix.lower() in UZANTILAR
               and not any(part.startswith(".") or part in {"web", "site-media", "thumbs", "thumbnails"}
                           for part in p.relative_to(root / "images").parts[:-1])
               and not p.name.startswith(".") and p.name != "simge.png"]
    result = {}
    for source in sources:
        src = source.relative_to(root).as_posix()
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        old = cache.get(src)
        if old and old.get("sha256") == digest and all(
                (root / item["src"]).exists() for item in old["variants"].values()):
            if source.suffix.lower() in {".jpg", ".jpeg"}:
                old["variants"]["full"]["src"] = src
                old["variants"]["full"]["bytes"] = source.stat().st_size
            result[src] = old
            continue
        image = rgb_kopya(source)
        # JPEG sources keep their filename and modification time; originals are never placed in the package.
        if source.suffix.lower() in {".jpg", ".jpeg"}:
            data = io.BytesIO()
            full = image.copy()
            full.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            full.save(data, "JPEG", quality=84, optimize=True, progressive=True,
                      icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
            if len(data.getvalue()) < source.stat().st_size or max(image.size) > 2048:
                stat = source.stat()
                if archive:
                    backup = root.parent / "Selim-Fotograf-Asillari" / src
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    if backup.exists() and backup.read_bytes() != source.read_bytes():
                        backup = backup.with_name(backup.stem + "-" + digest[:10] + backup.suffix)
                    if not backup.exists():
                        backup.write_bytes(source.read_bytes())
                source.write_bytes(data.getvalue())
                os.utime(source, (stat.st_atime, stat.st_mtime))
                image = full
        variants = {}
        for name, edge, quality in [("small", 480, 80), ("thumb", 960, 82),
                                    ("cover", 1600, 85), ("share", 1200, 82),
                                    ("full", 2048, 84)]:
            if name == "full" and source.suffix.lower() in {".jpg", ".jpeg"}:
                variants[name] = {"src": src, "width": image.width, "height": image.height,
                                  "bytes": source.stat().st_size}
                continue
            path = root / "site-media" / (dosya_kodu(src) + "-" + name + ".jpg")
            item = kaydet(image, path, edge, quality)
            item["src"] = path.relative_to(root).as_posix()
            variants[name] = item
        result[src] = {"sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "width": image.width, "height": image.height, "variants": variants}
    (root / "foto-web.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def image_tag(root, src, alt, role="thumb", loading="lazy", attrs=""):
    cache = json_oku(Path(root) / "foto-web.json", {})
    media = cache.get(src)
    if not media:
        raise ValueError("Web fotoğrafı hazırlanmadı: " + src)
    v = media["variants"]
    selected = v[role]
    sizes = "(max-width: 760px) 45vw, (max-width: 1100px) 33vw, 480px"
    if role == "cover":
        sizes = "(max-width: 760px) 25vw, (max-width: 1100px) 50vw, 40vw"
    if role == "full":
        sizes = "(max-width: 760px) 100vw, 880px"
    candidates = []
    keys = ["cover", "full"] if role == "cover" else ["small", "thumb", "cover"] + (["full"] if role == "full" else [])
    if role == "cover":
        # object-fit:cover fills tall columns; width-only 25vw would choose visibly blurred thumbnails.
        sizes = "(max-width: 760px) 100vh, (max-width: 1100px) 80vh, 70vw"
    for key in keys:
        item = v[key]
        if item["width"] not in [w for _, w in candidates]:
            candidates.append((item["src"], item["width"]))
    srcset = ", ".join(path + " " + str(width) + "w" for path, width in candidates)
    if 'hero-img' in attrs:
        sizes = '(max-width: 1100px) 100vw, 78vw'
    return ('<img src="' + html.escape(selected["src"]) + '" data-source="' + html.escape(src) +
            '" srcset="' + html.escape(srcset) + '" sizes="' + sizes + '" alt="' + html.escape(alt) +
            '" width="' + str(selected["width"]) + '" height="' + str(selected["height"]) +
            '" loading="' + loading + '" decoding="async" ' + attrs + '>')


def full_src(root, src):
    return json_oku(Path(root) / "foto-web.json", {})[src]["variants"]["full"]["src"]


def descriptions(root):
    return json_oku(Path(root) / "foto-aciklamalari.json", {})


def foto_alt(root, src, fallback):
    return descriptions(root).get(src, fallback)


def head_update(text, filename, root):
    url = SITE_URL if filename == "index.html" else SITE_URL + quote(filename)
    title = html.unescape(re.search(r"<title>(.*?)</title>", text, re.S).group(1))
    desc = re.search(r'<meta name="description" content="([^"]*)"', text).group(1)
    # Keep one metadata source, never concatenate conflicting tags.
    text = re.sub(r'<meta (?:property="og:[^"]+"|name="twitter:[^"]+")[^>]*>\s*', '', text)
    text = re.sub(r'<link rel="(?:canonical|icon|apple-touch-icon)"[^>]*>\s*', '', text)
    tags = ['<link rel="canonical" href="' + url + '">',
            '<link rel="icon" href="favicon.ico">',
            '<link rel="apple-touch-icon" href="images/simge.png">',
            '<meta property="og:title" content="' + html.escape(title) + '">',
            '<meta property="og:description" content="' + desc + '">',
            '<meta property="og:type" content="' + ('article' if filename in {
                'hikayeler1.html', 'hikayeler2.html', 'hikayeler3.html'} else 'website') + '">',
            '<meta property="og:url" content="' + url + '">',
            '<meta name="twitter:card" content="summary_large_image">']
    cache = json_oku(Path(root) / "foto-web.json", {})
    shown = re.findall(r'<img[^>]*data-source="([^"]+)"', text)
    if shown and html.unescape(shown[0]) in cache:
        share = cache[html.unescape(shown[0])]["variants"]["share"]
        photo_url = SITE_URL + quote(share["src"])
        tags += ['<meta property="og:image" content="' + photo_url + '">',
                 '<meta name="twitter:image" content="' + photo_url + '">']
    return text.replace('</head>', '\n'.join(tags) + '\n</head>')


def sayfalari_hazirla(root):
    root = Path(root)
    cache = json_oku(root / "foto-web.json", {})
    for page in root.glob('*.html'):
        text = page.read_text(encoding='utf-8')
        def replace_img(match):
            tag = match.group(0)
            source = re.search(r'data-source="([^"]+)"', tag) or re.search(r'\bsrc="([^"]+)"', tag)
            if not source:
                return tag
            src = html.unescape(source.group(1))
            if src not in cache:
                return tag
            alt = re.search(r'alt="([^"]*)"', tag)
            label = foto_alt(root, src, html.unescape(alt.group(1)) if alt else '')
            classes = re.search(r'class="([^"]*)"', tag)
            attrs = 'class="' + classes.group(1) + '"' if classes else ''
            if 'hero-img' in tag:
                role, loading, attrs = 'full', 'eager', attrs + ' fetchpriority="high"'
            elif page.name == 'portfolio.html':
                role, loading = 'cover', 'eager'
            elif page.name in {'hikayeler1.html','hikayeler2.html','hikayeler3.html'}:
                role, loading = 'full', 'eager'
            else:
                role, loading = ('cover' if page.name == 'hakkimda.html' else 'thumb'), ('eager' if 'loading="eager"' in tag or page.name == 'hakkimda.html' else 'lazy')
            return image_tag(root, src, label, role, loading, attrs)
        text = re.sub(r'<img\b[^>]*>', replace_img, text)
        # Only linked photographic files change; story destinations stay intact.
        def replace_link(match):
            tag = match.group(0)
            href = re.search(r'href="([^"]*)"', tag)
            if href:
                old_url = html.unescape(href.group(1))
                source = old_url if old_url in cache else next((src for src in cache
                    if old_url == 'site-media/' + dosya_kodu(src) + '-full.jpg'), None)
                if source:
                    return tag.replace(href.group(0), 'href="' + full_src(root, source) + '"')
            return tag
        text = re.sub(r'<a\b[^>]*>', replace_link, text)
        if page.name == 'site.html':
            text = text.replace('<h2>Görünenin ötesinde.</h2>', '<h1>Görünenin ötesinde.</h1>')
            text = re.sub(r' data-also="[^"]*"', '', text)
        # Static contacts remain useful if JavaScript is unavailable.
        text = re.sub(r'<span class="v" data-email-text>.*?</span>',
                      '<span class="v" data-email-text>selim.baltaci@gmail.com</span>', text)
        text = re.sub(r'<span class="v" data-instagram-text>.*?</span>',
                      '<span class="v" data-instagram-text>@pestepo</span>', text)
        text = re.sub(r'href="[^"]*" data-email', 'href="mailto:selim.baltaci@gmail.com" data-email', text)
        text = re.sub(r'href="[^"]*" data-instagram', 'href="https://www.instagram.com/pestepo/" data-instagram', text)
        if page.name == 'iletisim.html':
            text = text.replace('>Gönder <span', '>E-postayla gönder <span')
            text = text.replace('Gönder’e bastığınızda e-posta uygulamanız mesajınızla birlikte açılır.',
                'Mesajınızı e-posta uygulamanızda açıp oradan gönderebilirsiniz. Uygulama açılmazsa yukarıdaki e-posta adresini kullanın.')
        # Image interaction protection now has a single maintained home in site.js.
        text = re.sub(r'<script>\s*(?:/\* Fotoğraf koruması[\s\S]*?\*/\s*)?document.addEventListener\([\'\"]contextmenu[\s\S]*?</script>', '', text)
        text = text.replace('<aside class="drawer" id="menu"', '<aside class="drawer" role="dialog" aria-modal="true" tabindex="-1" id="menu"')
        text = head_update(text, page.name, root)
        page.write_text(text, encoding='utf-8')
    pages = sorted(p.name for p in root.glob('*.html'))
    urls = [SITE_URL if p == 'index.html' else SITE_URL + quote(p) for p in pages]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '\n'.join('  <url><loc>' + escape(url) + '</loc></url>' for url in urls) + '\n</urlset>\n'
    (root / 'sitemap.xml').write_text(xml, encoding='utf-8')
    (root / 'robots.txt').write_text('User-agent: *\nAllow: /\n\nSitemap: ' + SITE_URL + 'sitemap.xml\n', encoding='utf-8')


def sirayi_kaydet(root, orders):
    path = Path(root) / 'foto-sirasi.json'
    saved = json_oku(path, {})
    saved.update(orders)
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')