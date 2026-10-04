"""Tortlarga o'z rasmlarimizni qo'yish — avtomatik tanlash.

Ishga tushirish (loyiha papkasida):
    DJANGO_ENV_FILE=.env.production venv/bin/python manage.py shell < deploy/auto_cake_images.py

Qanday ishlaydi:
  1. SOURCE_DIRS dan rasmlarni skanerlaydi, sifatsizlarini (kichik, blur,
     qorongi, juda keng) va takrorlarini (dHash) chiqarib tashlaydi.
  2. Avval har bir tortga 1 asosiy rasm, keyin qolgan rasmgalereya sifatida
     navbatma-navbat bo'lib qo'shiladi.
  3. Rasmlarni tayyorlaydi: EXIF yo'nalishini to'g'rilaydi, 1400px gacha
     kichraytiradi (kattalashtirmaydi), yengil aniqlashtiradi, JPEG q88.

Yangi rasm qo'shish: uni SOURCE_DIRS ga kiring (masalan galereyaga
qo'yish uchun 'intagram uchun' papkasi) va skriptni qayta ishga tushiring.
"""

import glob
import hashlib
import os
import re

from PIL import Image, ImageFilter, ImageOps, ImageStat
from django.conf import settings

from cakes.models import Cake

# Rasmlar shu papkalardan olinadi (birinchisidan birinchi).
SOURCE_DIRS = [
    '/home/ubuntu/Pictures/rasmlar/intagram uchun',   # biznes uchun tayyorlangan
    '/home/ubuntu/Pictures/rasmlar',                  # umumiy albom
]

# Papka bo'lmagan manbalar — faqat galereya uchun (asosiy rasmga olinmaydi).
SOURCE_GLOBS = [
    '/home/ubuntu/Downloads/Gemini_Generated_Image_*.png',
]

# Dars/loyiha papkalari: u yerdagi rasmning aynan o'z albomimizga ko'chirilgan
# nusxasi bo'lsa, u dars materiali (odamlar, xizmatlar) — tortga mos emas.
BORROWED_DIRS = [
    '/home/ubuntu/Desktop/dars figma',
    '/home/ubuntu/Documents/VS code uchun',
    '/home/ubuntu/Desktop/loyihalarim/Maktab uchun crm',
    '/home/ubuntu/Desktop/loyihalarim/Restoran buyurtmasi',
]

# Bu papkalar/name'lar tashlab ketiladi:
SKIP_DIR_PARTS = ('anime',)
SKIP_NAME_PREFIXES = ('photo_',)   # dars/avatar rasmlari — tortga mos emas

MAX_SIDE = 1400
JPEG_QUALITY = 88
MIN_SIDE = 640           # asosiy rasm uchun minimal o'lcham
MIN_SIDE_GALLERY = 440   # galereya rasmi kichikroq chiqariladi — kamaytiriladi
MIN_SHARPNESS = 250      # blur rasm
MIN_BRIGHTNESS = 55      # juda qorongi rasm
MAX_ASPECT = 1.9         # juda keng (banner) rasm
MAX_GALLERY_PER_CAKE = 3


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def borrowed_hashes():
    """Dars/loyiha papkalaridagi rasmlarning md5 izohlari."""
    out = set()
    for root_dir in BORROWED_DIRS:
        for dirpath, _dirnames, filenames in os.walk(root_dir):
            for fn in filenames:
                if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    try:
                        out.add(md5(os.path.join(dirpath, fn)))
                    except OSError:
                        pass
    return out


def base_name(path):
    """'rasm (Edited).png' va 'rasm.png' — bitta rasmning ko'rinishlari."""
    return re.sub(r'\s*\(.*?\)\s*(?=\.[^.]+$)', '', os.path.basename(path)).lower()


def dhash(im, size=8):
    """Ko'rish uchun ixcham imzo — bir xil rasmlarni aniqlash uchun."""
    g = im.convert('L').resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = []
    for r in range(size):
        row = px[r * (size + 1):(r + 1) * (size + 1)]
        bits.extend(row[c] > row[c + 1] for c in range(size))
    return bits


def hamming(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


# Bir xil rasmni aniqlash: o'lcham/bayt soni bir xamda yoki imzo deyarli
# bir xamda bo'lsa — bu bitta rasmning ikki ko'rinishi (qayta saqlangan).
DUP_BITS = 2


def analyse(path):
    try:
        im = ImageOps.exif_transpose(Image.open(path))
        im.load()
    except Exception:
        return None
    w, h = im.size
    if min(w, h) < MIN_SIDE_GALLERY or max(w, h) / min(w, h) > MAX_ASPECT:
        return None

    small = im.copy()
    small.thumbnail((600, 600), Image.LANCZOS)
    sharp = ImageStat.Stat(small.convert('L').filter(ImageFilter.FIND_EDGES)).var[0]
    if sharp < MIN_SHARPNESS:
        return None
    if ImageStat.Stat(small.convert('L')).mean[0] < MIN_BRIGHTNESS:
        return None

    # Sifat bahosi: keskinlik + o'lcham + kvadratga yaqinlik
    score = min(sharp, 4000) / 100 + min(max(w, h), 2000) / 200
    score -= abs(1 - w / h) * 3
    return {
        'path': path, 'size': (w, h), 'score': score, 'hash': dhash(small),
        'bytes': os.path.getsize(path),
        # Asosiy rasmga faqat kattaroq rasm (portret/kvadrat) mos keladi
        'main_ok': min(w, h) >= MIN_SIDE,
    }


def prepare(src, dest_rel):
    """Rasmni tayyorlab media/ ichidagi dest_rel ga saqlaydi."""
    dest_abs = os.path.join(settings.MEDIA_ROOT, dest_rel)
    os.makedirs(os.path.dirname(dest_abs), exist_ok=True)

    im = ImageOps.exif_transpose(Image.open(src))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')

    if max(im.size) > MAX_SIDE:              # kichraytirish, kattalashtirish emas
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=3))
    im.save(dest_abs, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
    return dest_rel, os.path.getsize(dest_abs)


def scan():
    """Manba papkalardan noyob rasmlarni (takrorlarsiz) qaytaradi."""
    found = []
    borrowed = borrowed_hashes()

    sources = []
    for tier, root_dir in enumerate(SOURCE_DIRS):
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames
                           if d.lower() not in SKIP_DIR_PARTS]
            sources += [(os.path.join(dirpath, fn), tier) for fn in filenames]
    for pattern in SOURCE_GLOBS:
        sources += [(p, len(SOURCE_DIRS)) for p in sorted(glob.glob(pattern))]

    for path, tier in sources:
        fn = os.path.basename(path)
        if not fn.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            continue
        if fn.lower().startswith(SKIP_NAME_PREFIXES):
            continue
        try:
            if os.path.getsize(path) < 40_000:
                continue
            if md5(path) in borrowed:      # dars/loyiha materiali
                continue
        except OSError:
            continue
        info = analyse(path)
        if info:
            info['tier'] = tier
            info['base'] = base_name(path)
            found.append(info)

    # Sifatsiz raqam bo'yicha: avval biznes papkasi, keyin albom;
    # asosiy rasmga mos rasm galereya rasmlaridan oldin turadi.
    found.sort(key=lambda c: (c['tier'], not c['main_ok'], -c['score']))

    unique = []
    for c in found:
        same = any(
            c['base'] == u['base']                    # "(Edited)" ko'rinishlari
            or (c['size'] == u['size'] and abs(c['bytes'] - u['bytes']) < 1024)
            or hamming(c['hash'], u['hash']) <= DUP_BITS
            for u in unique
        )
        if not same:
            unique.append(c)
    return found, unique


def show(tag, info, size_kb):
    print('%-7s %-20s %4dx%-4d %5.0f KB  %s'
          % (tag, info['slug'], info['size'][0], info['size'][1], size_kb / 1024,
             os.path.basename(info['path'])[:40]))


total, pool = scan()
cakes = list(Cake.objects.order_by('id'))

if not pool:
    raise SystemExit('Mos rasm topilmadi. SOURCE_DIRS ni tekshiring.')

# 0) Eski galereyani to'liq tozalash — takror qatorlar qolmasligi uchun.
#    Kerak bo'lmagan fayllar oxirida, boshqa joyda ishlatilmagani tekshirilib
#    o'chiriladi.
stale_files = []
for cake in cakes:
    for old in cake.images.all():
        stale_files.append(old.image.name)
        old.delete()

# 1) Har bir tortga asosiy rasm
queue = list(pool)
for cake in cakes:
    idx = next((i for i, c in enumerate(queue) if c['main_ok']), None)
    if idx is None:
        break
    info = queue.pop(idx)
    info['slug'] = cake.slug
    rel, size = prepare(info['path'], 'cakes/%s.jpg' % cake.slug)
    stale_files.append(cake.main_image.name)
    cake.main_image.name = rel
    cake.save(update_fields=['main_image'])
    show('asosiy', info, size)

# 2) Qolgan rasmgalereya sifatida navbatma-navbat
added = {c.slug: 0 for c in cakes}
while queue and max(added.values()) < MAX_GALLERY_PER_CAKE:
    for cake in cakes:
        if not queue or added[cake.slug] >= MAX_GALLERY_PER_CAKE:
            continue
        info = queue.pop(0)
        info['slug'] = cake.slug
        n = added[cake.slug] + 1
        rel, size = prepare(info['path'], 'cakes/gallery/%s-%d.jpg' % (cake.slug, n))
        cake.images.create(image=rel)     # fayl allaqachon media/ da tayyor
        added[cake.slug] = n
        show('galer.%d' % n, info, size)

# 3) Endi hech qanday rasmga bog'lanmagan fayllarni o'chirish
used = set(Cake.objects.values_list('main_image', flat=True))
for cake in cakes:
    used.update(cake.images.values_list('image', flat=True))
removed = 0
for name in dict.fromkeys(stale_files):
    if name in used:
        continue
    path = os.path.join(settings.MEDIA_ROOT, name)
    if os.path.isfile(path):
        os.remove(path)
        removed += 1

print('\nSkanerlangan: %d, takrordan keyin: %d, ishlatildi: %d'
      % (len(total), len(pool), len(pool) - len(queue)))
print('Tozalangan eski fayl: %d' % removed)
print('Almashish: /admin/cakes/cake/')
