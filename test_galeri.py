# -*- coding: utf-8 -*-
"""python3 -m unittest test_galeri.py — fotoğraf kuralları ve güvenli yeniden üretim."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from PIL import Image
import galeriyi_guncelle as gallery
import web_fotograflari as web


class GalleryRules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'site'
        (self.root / 'images' / 'monochrom').mkdir(parents=True)
        self.old_root = gallery.KLASOR
        gallery.KLASOR = str(self.root)

    def tearDown(self):
        gallery.KLASOR = self.old_root
        self.temp.cleanup()

    def photo(self, name, size=(120, 80), color=(40, 130, 220)):
        path = self.root / 'images' / 'monochrom' / name
        Image.new('RGB', size, color).save(path, quality=90)
        return path.relative_to(self.root).as_posix(), str(path)

    def test_four_series_in_requested_order(self):
        self.assertEqual([s[3] for s in gallery.SERILER],
                         ['Monochrom', 'Yanılsamalar', 'Seçilmiş Kareler', 'Yeni Kareler'])

    def test_new_photo_first_after_two_runs(self):
        old = self.photo('old.JPG')
        web.sirayi_kaydet(self.root, {'monochrom': [old[0]]})
        new = self.photo('new.JPG')
        os.utime(new[1], (20, 20))
        for _ in range(2):
            web.hazirla(self.root, archive=False)
            rows = web.sirali_fotograflar(self.root, 'monochrom')
            self.assertEqual([src for src, _ in rows], [new[0], old[0]])
            web.sirayi_kaydet(self.root, {'monochrom': [src for src, _ in rows]})

    def test_derived_images_do_not_duplicate_entries(self):
        self.photo('original.JPG')
        generated = self.root / 'images' / 'monochrom' / 'thumbs'
        generated.mkdir()
        Image.new('RGB', (20, 20)).save(generated / 'duplicate.jpg')
        web.hazirla(self.root, archive=False)
        self.assertEqual(len(web.sirali_fotograflar(self.root, 'monochrom')), 1)

    def test_first_40_then_40_with_all_viewer_links(self):
        photos = [self.photo('foto%03d.JPG' % i) for i in range(85)]
        web.hazirla(self.root, archive=False)
        markup = gallery.temas_baskisi('Monochrom', photos)
        self.assertEqual(markup.count('class="s-item"'), 40)
        self.assertEqual(markup.count('class="s-item is-later"'), 45)
        self.assertEqual(markup.count('<a class="s-item'), 85)
        self.assertIn('data-step="40"', markup)

    def test_full_web_photo_never_exceeds_2048(self):
        src, _ = self.photo('large.JPG', size=(5000, 3000))
        media = web.hazirla(self.root, archive=False)[src]
        self.assertEqual((media['width'], media['height']), (2048, 1229))
        self.assertLessEqual(max(media['variants']['full']['width'], media['variants']['full']['height']), 2048)

    def test_original_color_remains_color(self):
        src, _ = self.photo('blue.JPG')
        media = web.hazirla(self.root, archive=False)[src]
        with Image.open(self.root / media['variants']['full']['src']) as im:
            r, g, b = im.getpixel((20, 20))
        self.assertGreater(b - r, 100)
        self.assertGreater(g - r, 40)

    def test_portrait_ratio_uncropped(self):
        src, _ = self.photo('portrait.JPG', size=(80, 120))
        media = web.hazirla(self.root, archive=False)[src]
        self.assertEqual((media['width'], media['height']), (80, 120))
        self.assertIn('--r:0.666667', gallery.temas_baskisi('Monochrom', [(src, str(self.root / src))]))

    def test_regeneration_keeps_icon_and_protection(self):
        photo = self.photo('one.JPG')
        web.hazirla(self.root, archive=False)
        output = gallery.galeri_sayfasi(0, [photo])
        self.assertIn('href="images/simge.png"', output)
        self.assertIn('href="favicon.ico"', output)
        self.assertIn('contextmenu', output)
        self.assertIn('dragstart', output)

    def test_cache_does_not_recompress_unchanged_photos(self):
        src, _ = self.photo('same.JPG', size=(2500, 1600))
        web.hazirla(self.root, archive=False)
        digest = hashlib.sha256((self.root / src).read_bytes()).hexdigest()
        first = web.json_oku(self.root / 'foto-web.json', {})
        web.hazirla(self.root, archive=False)
        self.assertEqual(first, web.json_oku(self.root / 'foto-web.json', {}))
        self.assertEqual(digest, hashlib.sha256((self.root / src).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()