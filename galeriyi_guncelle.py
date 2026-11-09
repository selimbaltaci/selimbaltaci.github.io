# -*- coding: utf-8 -*-
"""
GALERİYİ GÜNCELLE  —  Düşler ve Yanılsamalar

Ne yapar?
  1) images/ altındaki dört klasöre bakar:
       images/monochrom          -> monochrom.html
       images/yanilsamalar       -> yanilsamalar.html
       images/secilmis-kareler   -> secilmis-kareler.html
       images/yeni-kareler       -> yeni-kareler.html
     Her klasördeki fotoğrafları EN YENİ EN ÜSTTE olacak şekilde sıralar
     ve dört galeri sayfasını beyaz tasarımla yeniden yazar.
  2) site.html içindeki "Yeni Kareler" kutusuna images/yeni-kareler
     klasöründeki en yeni 7 fotoğrafı yerleştirir (dikeyler dikey kutuya,
     yataylar yatay kutuya; 7'den az varsa diğer serilerden tamamlar).

Kullanım (Terminal, site klasörünün içinde):
    python3 galeriyi_guncelle.py
"""
import os
import re
import struct
import html
import unicodedata

KLASOR = os.path.dirname(os.path.abspath(__file__))
UZANTILAR = (".jpg", ".jpeg", ".png", ".webp", ".gif")
ANA_SAYFA_ADET = 7

# "Temas baskısı" düzenini kullanan galeriler. Diğerleri eski duvar düzeninde kalır.
# Hepsine uygulamak için: TEMAS_DUZENI = ["monochrom", "yanilsamalar", "secilmis-kareler", "yeni-kareler"]
TEMAS_DUZENI = ["monochrom", "yanilsamalar", "secilmis-kareler", "yeni-kareler"]
# Sayfa açıldığında kaç kare görünsün; "Daha fazla kare göster" her basışta bu kadar daha açar.
PARTI = 40

# (sayfa, klasör adayları, numara, başlık, açıklama)
SERILER = [
    ("monochrom", ["monochrom", "monochorom"], "01", "Monochrom",
     "Işık, gölge ve sessizlik üzerine siyah-beyaz kareler."),
    ("yanilsamalar", ["yanilsamalar", "yanılsamalar"], "02", "Yanılsamalar",
     "Gördüğümüzle gerçek sandığımız şey arasındaki belirsiz çizgi."),
    ("secilmis-kareler", ["secilmis-kareler", "seçilmiş-kareler", "secilmis_kareler"], "03", "Seçilmiş Kareler",
     "Farklı zamanlardan, farklı hikâyelerden seçilmiş fotoğraflar."),
    ("yeni-kareler", ["yeni-kareler", "yeni_kareler"], "04", "Yeni Kareler",
     "Son çekimlerimden yeni karşılaşmalar ve yeni izler."),
]

MENU = [
    ("site.html#akis", "01", "Ana Sayfa"),
    ("portfolio.html", "02", "Portfolyo"),
    ("hikayeler.html", "03", "Karelerin Ardında"),
    ("hakkimda.html", "04", "Hakkımda"),
    ("iletisim.html", "05", "İletişim"),
]

NL = "\n"


# ------------------------------------------------------------------ ölçü
def jpeg_olcu(f):
    """JPEG genişlik/yükseklik; telefonun döndürme bilgisini (EXIF) de dikkate alır."""
    f.seek(2)
    yon = 1
    while True:
        b = f.read(1)
        while b and b != b"\xff":
            b = f.read(1)
        while b == b"\xff":
            b = f.read(1)
        if not b:
            return None
        isaret = b[0]
        if isaret in (0xD8, 0x01) or 0xD0 <= isaret <= 0xD7:
            continue
        uzunluk = struct.unpack(">H", f.read(2))[0]
        veri_bas = f.tell()
        if isaret == 0xE1:
            veri = f.read(uzunluk - 2)
            if veri[:6] == b"Exif\x00\x00":
                yon = exif_yon(veri[6:]) or 1
        elif isaret in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            f.read(1)
            h, w = struct.unpack(">HH", f.read(4))
            if yon in (5, 6, 7, 8):
                w, h = h, w
            return w, h
        f.seek(veri_bas + uzunluk - 2)


def exif_yon(t):
    try:
        e = "<" if t[:2] == b"II" else ">"
        ofs = struct.unpack(e + "I", t[4:8])[0]
        n = struct.unpack(e + "H", t[ofs:ofs + 2])[0]
        for i in range(n):
            g = ofs + 2 + i * 12
            etiket = struct.unpack(e + "H", t[g:g + 2])[0]
            if etiket == 0x0112:
                return struct.unpack(e + "H", t[g + 8:g + 10])[0]
    except Exception:
        return None
    return None


def olcu(yol):
    try:
        with open(yol, "rb") as f:
            bas = f.read(26)
            if bas[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", bas[16:24])
            if bas[:2] == b"\xff\xd8":
                return jpeg_olcu(f)
    except Exception:
        return None
    return None


# ------------------------------------------------------------------ klasör
def _sade(ad):
    """Klasör adını karşılaştırmak için sadeleştirir:
    büyük/küçük harf, Türkçe harf, boşluk ve alt çizgi farkını yok sayar."""
    ad = unicodedata.normalize("NFC", ad).strip().lower()
    for a, b in (("ı", "i"), ("i̇", "i"), ("ş", "s"), ("ç", "c"), ("ğ", "g"), ("ü", "u"), ("ö", "o")):
        ad = ad.replace(a, b)
    ad = unicodedata.normalize("NFKD", ad)
    ad = "".join(c for c in ad if not unicodedata.combining(c))
    return re.sub(r"[\s_\-]+", "-", ad)


def klasor_bul(adaylar):
    """images içindeki klasörü bulur. "Yeni Kareler", "yeni_kareler",
    "YENİ-KARELER" gibi yazımların hepsi aynı klasör sayılır."""
    kok = os.path.join(KLASOR, "images")
    hedefler = set(_sade(a) for a in adaylar)
    if os.path.isdir(kok):
        for ad in sorted(os.listdir(kok)):
            if os.path.isdir(os.path.join(kok, ad)) and _sade(ad) in hedefler:
                return ad
    return adaylar[0]


def fotograflar(klasor_adi):
    yol = os.path.join(KLASOR, "images", klasor_adi)
    if not os.path.isdir(yol):
        return []
    liste = []
    for kok, klasorler, dosyalar in os.walk(yol):
        klasorler[:] = [k for k in klasorler if not k.startswith(".")]
        for ad in dosyalar:
            if ad.startswith(".") or not ad.lower().endswith(UZANTILAR):
                continue
            tam = os.path.join(kok, ad)
            src = os.path.relpath(tam, KLASOR).replace(os.sep, "/")
            liste.append((os.path.getmtime(tam), src, tam))
    liste.sort(key=lambda x: x[0], reverse=True)   # en yeni en üstte
    return [(src, tam) for _, src, tam in liste]


def klasoru_anlat(klasor_adi):
    """Bir seride hiç fotoğraf bulunamazsa nedenini ekrana yazar."""
    kok = os.path.join(KLASOR, "images")
    yol = os.path.join(kok, klasor_adi)
    if not os.path.isdir(yol):
        print("      ! images içinde '" + klasor_adi + "' klasörü yok.")
        if os.path.isdir(kok):
            adlar = [a for a in sorted(os.listdir(kok)) if os.path.isdir(os.path.join(kok, a))]
            print("        images içindeki klasörler: " + ", ".join(adlar))
        return
    icerik = [a for a in sorted(os.listdir(yol)) if not a.startswith(".")]
    if not icerik:
        print("      ! '" + klasor_adi + "' klasörü boş.")
    else:
        print("      ! '" + klasor_adi + "' içinde fotoğraf sayılmayan dosyalar var: " + ", ".join(icerik[:8]))
        print("        Desteklenen türler: JPG, JPEG, PNG, WEBP, GIF")


# ------------------------------------------------------------------ sayfa
def menu_html(aktif):
    satirlar = []
    for href, n, t in MENU:
        cur = ' aria-current="page"' if href == aktif else ""
        satirlar.append('      <a href="' + href + '"' + cur + '><span class="n">' + n +
                        '</span><span class="t">' + t + '</span></a>')
    return NL.join(satirlar)


def temas_baskisi(baslik, foto_listesi):
    """Temas baskısı düzeni: fotoğraflar eşit yükseklikte satırlara dizilir,
    dikey ve yataylar kırpılmadan kendi oranında durur. En yeni en üstte, soldan sağa.
    İlk PARTI kadar kare görünür; kalanı "Daha fazla kare göster" ile açılır."""
    if not foto_listesi:
        return '  <p class="empty wrap">Bu seriye yakında yeni kareler eklenecek.</p>'
    toplam = len(foto_listesi)
    kareler = []
    for k, (src, tam) in enumerate(foto_listesi):
        boyut = olcu(tam)
        oran = 1.333
        wh = ""
        if boyut and boyut[0] and boyut[1]:
            oran = max(0.4, min(3.0, boyut[0] / float(boyut[1])))
            wh = ' width="' + str(boyut[0]) + '" height="' + str(boyut[1]) + '"'
        sonra = " is-later" if k >= PARTI else ""
        e = html.escape(src)
        kareler.append('    <a class="s-item' + sonra + '" href="' + e + '" style="--r:' + ("%.3f" % oran) +
                       '"><img src="' + e + '" alt="' + baslik + ' fotoğraf ' + str(k + 1) + '"' + wh +
                       ' loading="lazy" decoding="async"><span class="s-no caps">' + str(k + 1).zfill(2) + '</span></a>')
    blok = ('  <section class="sheet wrap" data-lightbox data-title="' + baslik +
            '" aria-label="' + baslik + ' fotoğrafları">' + NL + NL.join(kareler) + NL + '  </section>')
    if toplam > PARTI:
        blok += (NL + '  <div class="sheet-more" data-sheet-more data-step="' + str(PARTI) + '">' + NL +
                 '    <span class="caps sheet-count">' + str(PARTI) + ' / ' + str(toplam) + ' kare</span>' + NL +
                 '    <button class="more-btn caps" type="button">Daha fazla kare göster</button>' + NL +
                 '  </div>')
    return blok


DAHA_FAZLA_JS = """<script>
(function () {
    var box = document.querySelector("[data-sheet-more]");
    if (!box) return;
    var step = +box.getAttribute("data-step") || 40;
    var btn = box.querySelector("button");
    var count = box.querySelector(".sheet-count");
    var total = document.querySelectorAll(".s-item").length;
    btn.addEventListener("click", function () {
        var rest = document.querySelectorAll(".s-item.is-later");
        for (var i = 0; i < step && i < rest.length; i++) {
            rest[i].classList.remove("is-later");
            rest[i].classList.add("is-new");
        }
        var left = document.querySelectorAll(".s-item.is-later").length;
        count.textContent = (total - left) + " / " + total + " kare";
        if (!left) btn.hidden = true;
    });
})();
</script>
"""


def galeri_sayfasi(i, foto_listesi):
    sayfa, _, numara, baslik, aciklama = SERILER[i]
    onceki = SERILER[(i - 1) % len(SERILER)]
    sonraki = SERILER[(i + 1) % len(SERILER)]

    sekmeler = []
    for s in SERILER:
        cur = ' aria-current="page"' if s[0] == sayfa else ""
        sekmeler.append('  <a href="' + s[0] + '.html"' + cur + '><span class="n">' + s[2] +
                        '</span><span>' + s[3] + '</span></a>')

    ek_js = ""
    if sayfa in TEMAS_DUZENI:
        galeri = temas_baskisi(baslik, foto_listesi)
        ek_js = DAHA_FAZLA_JS
    else:
        kareler = []
        for src, tam in foto_listesi:
            boyut = olcu(tam)
            wh = ""
            if boyut:
                wh = ' width="' + str(boyut[0]) + '" height="' + str(boyut[1]) + '"'
            kareler.append('    <a class="g-item reveal" href="' + html.escape(src) + '"><img src="' +
                           html.escape(src) + '" alt="' + baslik + ' fotoğraf"' + wh +
                           ' loading="lazy" decoding="async"></a>')
        if kareler:
            galeri = ('  <section class="masonry wrap" data-lightbox data-title="' + baslik +
                      '" aria-label="' + baslik + ' fotoğrafları">' + NL + NL.join(kareler) + NL + '  </section>')
        else:
            galeri = '  <p class="empty wrap">Bu seriye yakında yeni kareler eklenecek.</p>'

    adet = str(len(foto_listesi))
    return """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>""" + baslik + """ | Düşler ve Yanılsamalar — Selim Baltacı</title>
<meta name="description" content=\"""" + aciklama + """\">
<meta property="og:title" content=\"""" + baslik + """ — Selim Baltacı\">
<meta property="og:description" content=\"""" + aciklama + """\">
<meta property="og:type" content="website">
<meta name="theme-color" content="#faf9f7">
<script>document.documentElement.className = "js";</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Allura&family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=IBM+Plex+Mono:wght@300;400&family=Jost:wght@300;400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/site.css">
<link rel="icon" href="favicon.ico">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
</head>
<body id="top">
  <!-- Bu sayfa galeriyi_guncelle.py tarafından oluşturulur. Elle değiştirmeyin. -->
  <header class="topbar wrap">
    <a class="brand" href="site.html#akis">Düşler ve Yanılsamalar <span>/ Selim Baltacı</span></a>
    <button class="burger" type="button" aria-label="Menüyü aç" aria-expanded="false" aria-controls="menu"><span></span><span></span><span></span></button>
  </header>

<nav class="tabs" aria-label="Seriler">
""" + NL.join(sekmeler) + """
</nav>

<main>
  <header class="series-head wrap">
    <div class="back"><a class="caps" href="portfolio.html">← Tüm seriler</a></div>
    <div class="intro">
      <span class="caps" style="color:var(--muted)">Seri """ + numara + " · " + adet + """ kare</span>
      <h1>""" + baslik + """</h1>
      <p class="lead">""" + aciklama + """</p>
    </div>
  </header>

""" + galeri + """
</main>

<nav class="pager wrap" aria-label="Diğer seriler">
  <a href=\"""" + onceki[0] + """.html"><span class="k caps">← Önceki seri</span><span class="name">""" + onceki[3] + """</span></a>
  <a href=\"""" + sonraki[0] + """.html"><span class="k caps">Sonraki seri →</span><span class="name">""" + sonraki[3] + """</span></a>
</nav>

<footer class="site-footer wrap caps">
  <span>© 2026 Selim Baltacı · Tüm hakları saklıdır</span>
  <a href="portfolio.html">Portfolyoya dön ↑</a>
</footer>

<div class="scrim" data-close-menu></div>
<aside class="drawer" id="menu" aria-label="Site menüsü" aria-hidden="true">
  <div class="drawer-head">
    <span class="caps">Menü</span>
    <button class="drawer-close" type="button" aria-label="Menüyü kapat" data-close-menu>×</button>
  </div>
  <nav>
""" + menu_html("portfolio.html") + """
  </nav>
  <p class="drawer-foot caps">Düşler ve Yanılsamalar · Selim Baltacı</p>
</aside>

<script src="js/site.js"></script>
<script>
/* Fotoğraf koruması: sağ tık ve sürükleme kapalı (betik her seferinde ekler) */
document.addEventListener("contextmenu", function (e) { if (e.target.tagName === "IMG") e.preventDefault(); });
document.addEventListener("dragstart", function (e) { if (e.target.tagName === "IMG") e.preventDefault(); });
</script>
""" + ek_js + """</body>
</html>
"""


def yonu(tam):
    o = olcu(tam)
    if not o or not o[0] or not o[1]:
        return "?"
    g, y = o
    if y > g * 1.08:
        return "dikey"
    if g > y * 1.15:
        return "yatay"
    return "kare"


def kutulara_yerlestir(liste):
    """7 kutulu mozaik: 1 ve 5 dikey, 2-6-7 yatay, 3-4 küçük.
    En yeni fotoğraflar önce gelir; dikeyler dikey, yataylar yatay kutuya."""
    dikey_kutu = [0, 4]
    yatay_kutu = [1, 5, 6]
    kucuk_kutu = [2, 3]
    kutular = [None] * len(liste)
    kalan = []
    for foto in liste:
        yon = yonu(foto[1])
        if yon == "dikey" and dikey_kutu:
            kutular[dikey_kutu.pop(0)] = foto
        elif yon == "yatay" and yatay_kutu:
            kutular[yatay_kutu.pop(0)] = foto
        else:
            kalan.append(foto)
    bos = sorted([k for k in dikey_kutu + yatay_kutu + kucuk_kutu if k < len(liste)])
    for k, foto in zip(bos, kalan):
        kutular[k] = foto
    return [f for f in kutular if f]


def ana_sayfayi_guncelle(yeni_liste, diger_listeler):
    yol = os.path.join(KLASOR, "site.html")
    if not os.path.exists(yol):
        print("  ! site.html bulunamadı, ana sayfa atlandı.")
        return
    with open(yol, encoding="utf-8") as f:
        metin = f.read()
    secilen = list(yeni_liste[:ANA_SAYFA_ADET])
    eklenen = 0
    if len(secilen) < ANA_SAYFA_ADET:
        # Yeni Kareler klasöründe 7'den az fotoğraf varsa, düzen bozulmasın diye
        # diğer serilerin en yeni fotoğraflarıyla tamamlanır.
        havuz = []
        for liste in diger_listeler:
            for src, tam in liste:
                havuz.append((os.path.getmtime(tam), src, tam))
        havuz.sort(key=lambda x: x[0], reverse=True)
        mevcut = set(s for s, _ in secilen)
        for _, src, tam in havuz:
            if len(secilen) >= ANA_SAYFA_ADET:
                break
            if src not in mevcut:
                secilen.append((src, tam))
                mevcut.add(src)
                eklenen += 1
    if not secilen:
        print("  ! Hiç fotoğraf bulunamadı; ana sayfadaki Yeni Kareler kutusuna dokunulmadı.")
        return
    satirlar = []
    for src, _ in kutulara_yerlestir(secilen):
        s = html.escape(src)
        satirlar.append('<a class="photo-placeholder" href="' + s + '"><img src="' + s +
                        '" alt="Yeni Kareler fotoğraf" loading="lazy"></a>')
    desen = re.compile(r'(<div class="new-photos"[^>]*>)[\s\S]*?(</div>\s*<!-- YENİ KARELER BİTİŞ -->)')
    if not desen.search(metin):
        print("  ! site.html içinde Yeni Kareler kutusu bulunamadı, ana sayfa atlandı.")
        return
    yeni_blok = lambda m: m.group(1) + NL + NL.join(satirlar) + NL + m.group(2)
    metin = desen.sub(yeni_blok, metin, count=1)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)
    not_ = ""
    if eklenen:
        not_ = ", " + str(eklenen) + " tanesi diğer serilerden tamamlandı"
    print("  ✓ site.html  →  Yeni Kareler kutusu (" + str(len(satirlar)) + " fotoğraf" + not_ + ")")


def main():
    print("Galeriler güncelleniyor…")
    yeni_liste = []
    diger_listeler = []
    for i, s in enumerate(SERILER):
        klasor_adi = klasor_bul(s[1])
        liste = fotograflar(klasor_adi)
        with open(os.path.join(KLASOR, s[0] + ".html"), "w", encoding="utf-8") as f:
            f.write(galeri_sayfasi(i, liste))
        print("  ✓ " + s[0] + ".html  ←  images/" + klasor_adi + "  (" + str(len(liste)) + " fotoğraf)")
        if not liste:
            klasoru_anlat(klasor_adi)
        if s[0] == "yeni-kareler":
            yeni_liste = liste
        else:
            diger_listeler.append(liste)
    ana_sayfayi_guncelle(yeni_liste, diger_listeler)
    print("✨ İŞLEM TAMAM: Tüm galeri sayfaları ve site.html güncellendi!")


if __name__ == "__main__":
    main()
