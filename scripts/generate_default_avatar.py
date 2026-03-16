#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'avatars')
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, 'default_avatar.png')

def lerp(a, b, t):
    return int(a + (b - a) * t)

def make_avatar(size=256):
    # Colors from the SVG gradient
    top = (102, 126, 234)
    bottom = (118, 75, 162)

    img = Image.new('RGBA', (size, size))
    draw = ImageDraw.Draw(img)

    # vertical gradient
    for y in range(size):
        t = y / (size - 1)
        r = lerp(top[0], bottom[0], t)
        g = lerp(top[1], bottom[1], t)
        b = lerp(top[2], bottom[2], t)
        draw.line([(0, y), (size, y)], fill=(r, g, b))

    # white circle (head)
    cx, cy, r = int(size * 0.35), int(size * 0.35), int(size * 0.16)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 230))

    # rounded rectangle body
    body_w = int(size * 0.55)
    body_h = int(size * 0.18)
    bx = int(size * 0.06)
    by = int(size * 0.62)
    br = int(body_h * 0.4)
    # draw rounded rect manually
    draw.rounded_rectangle([bx, by, bx + body_w, by + body_h], radius=br, fill=(255,255,255,230))

    return img

if __name__ == '__main__':
    img = make_avatar(256)
    img.save(OUT_PATH, format='PNG')
    print('Wrote', OUT_PATH)
