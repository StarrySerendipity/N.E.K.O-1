# -*- coding: utf-8 -*-
"""生成十二星座深空星图卡片（真实恒星坐标 J2000 + 经典连线 + PIL 渲染）。

风格：深空靛紫渐变背景 + 星云辉光 + 星点 + 星座连线辉光 + 中英双语标注。
输出：plugin/plugins/tarot/static/image/zodiac/<key>.png (800x1200)
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "static", "image", "zodiac"))
W, H = 800, 1200
FONT_DIR = "C:/Windows/Fonts"
F_CN_BOLD = os.path.join(FONT_DIR, "msyhbd.ttc")
F_CN = os.path.join(FONT_DIR, "msyh.ttc")
F_EN = os.path.join(FONT_DIR, "segoeui.ttf")
F_SYM = os.path.join(FONT_DIR, "seguisym.ttf")

# ─────────────────────────────────────────────────────────────
# 星座数据：key, 中文名, 英文名, 符号, 日期, 元素, 守护星
# 恒星: (标识, RA小时, Dec度, 视星等, 中文标注, 英文标注)
# 连线: 恒星标识对
# ─────────────────────────────────────────────────────────────
ZODIAC = {
    "aries": dict(cn="白羊座", en="ARIES", sym="♈", dates="3.21 - 4.19", element="火象 · 守护星 火星", stars=[
        ("hamal", 2.025, 23.46, 2.01, "娄宿三", "α Hamal"),
        ("sheratan", 1.911, 20.81, 2.64, None, "β Sheratan"),
        ("mesarthim", 1.893, 19.29, 3.88, None, "γ Mesarthim"),
        ("41ari", 2.833, 27.26, 3.63, None, "41 Ari"),
    ], lines=[("mesarthim", "sheratan"), ("sheratan", "hamal"), ("hamal", "41ari")]),
    "taurus": dict(cn="金牛座", en="TAURUS", sym="♉", dates="4.20 - 5.20", element="土象 · 守护星 金星", stars=[
        ("aldebaran", 4.599, 16.51, 0.86, "毕宿五", "α Aldebaran"),
        ("elnath", 5.438, 28.61, 1.65, None, "β Elnath"),
        ("zetatau", 5.627, 21.14, 3.00, None, "ζ"),
        ("gamtau", 4.330, 15.63, 3.65, None, "γ"),
        ("deltatau", 4.382, 17.54, 3.73, None, "δ"),
        ("epstau", 4.477, 19.18, 3.53, None, "ε"),
        ("lampdau", 4.011, 12.49, 3.47, None, "λ"),
        ("xitau", 4.954, 19.37, 3.73, None, "ξ"),
    ], lines=[("lampdau", "gamtau"), ("gamtau", "deltatau"), ("deltatau", "epstau"),
              ("gamtau", "aldebaran"), ("deltatau", "elnath"), ("epstau", "xitau"), ("xitau", "zetatau")]),
    "gemini": dict(cn="双子座", en="GEMINI", sym="♊", dates="5.21 - 6.21", element="风象 · 守护星 水星", stars=[
        ("castor", 7.577, 31.89, 1.58, "北河二", "α Castor"),
        ("pollux", 7.755, 28.03, 1.14, "北河三", "β Pollux"),
        ("alhena", 6.629, 16.40, 1.93, None, "γ Alhena"),
        ("wasat", 7.335, 21.98, 3.53, None, "δ Wasat"),
        ("mebsuta", 6.732, 25.13, 2.98, None, "ε"),
        ("mekbuda", 7.069, 20.57, 3.79, None, "ζ"),
        ("tejat", 6.383, 22.51, 2.88, None, "μ Tejat"),
        ("propus", 6.248, 22.51, 3.31, None, "η"),
        ("xigem", 7.272, 30.86, 3.31, None, "ξ"),
        ("kappagem", 7.739, 24.40, 3.57, None, "κ"),
    ], lines=[("castor", "xigem"), ("xigem", "mebsuta"), ("mebsuta", "tejat"), ("tejat", "propus"),
              ("pollux", "kappagem"), ("kappagem", "wasat"), ("wasat", "mekbuda"), ("mekbuda", "alhena"),
              ("mebsuta", "wasat")]),
    "cancer": dict(cn="巨蟹座", en="CANCER", sym="♋", dates="6.22 - 7.22", element="水象 · 守护星 月亮", stars=[
        ("acubens", 8.975, 11.86, 3.94, None, "α Acubens"),
        ("tarf", 8.275, 9.20, 3.53, None, "β Tarf"),
        ("asellus_a", 8.745, 18.15, 3.94, None, "δ"),
        ("asellus_b", 8.719, 21.47, 4.66, None, "γ"),
        ("iotacnc", 8.778, 28.76, 4.02, None, "ι"),
    ], lines=[("acubens", "asellus_a"), ("tarf", "asellus_a"), ("asellus_a", "asellus_b"), ("asellus_b", "iotacnc")]),
    "leo": dict(cn="狮子座", en="LEO", sym="♌", dates="7.23 - 8.22", element="火象 · 守护星 太阳", stars=[
        ("regulus", 10.139, 11.97, 1.36, "轩辕十四", "α Regulus"),
        ("denebola", 11.818, 14.57, 2.14, None, "β Denebola"),
        ("algieba", 10.333, 19.84, 2.08, None, "γ Algieba"),
        ("zosma", 11.235, 20.52, 2.56, None, "δ Zosma"),
        ("raselased", 9.764, 23.77, 2.97, None, "ε"),
        ("adhafera", 10.279, 23.42, 3.44, None, "ζ"),
        ("chertan", 11.237, 15.43, 3.33, None, "θ"),
        ("etaleo", 10.122, 16.76, 3.51, None, "η"),
        ("muleo", 9.879, 26.00, 3.88, None, "μ"),
    ], lines=[("muleo", "raselased"), ("raselased", "adhafera"), ("adhafera", "algieba"),
              ("algieba", "etaleo"), ("etaleo", "regulus"), ("regulus", "chertan"),
              ("chertan", "denebola"), ("denebola", "zosma"), ("zosma", "algieba")]),
    "virgo": dict(cn="处女座", en="VIRGO", sym="♍", dates="8.23 - 9.22", element="土象 · 守护星 水星", stars=[
        ("spica", 13.420, -11.16, 0.98, "角宿一", "α Spica"),
        ("zavijava", 11.845, 1.76, 3.60, None, "β"),
        ("porrima", 12.694, -1.45, 2.74, None, "γ Porrima"),
        ("auva", 12.927, 3.40, 3.38, None, "δ"),
        ("vindemiatrix", 13.036, 10.96, 2.85, None, "ε"),
        ("heze", 13.578, -0.60, 3.38, None, "ζ"),
        ("zaniah", 12.332, -0.67, 3.89, None, "η"),
        ("thetavir", 13.166, -5.54, 4.38, None, "θ"),
        ("iotavir", 14.268, -6.00, 4.07, None, "ι"),
        ("109vir", 14.771, 1.54, 3.73, None, "109"),
    ], lines=[("zavijava", "zaniah"), ("zaniah", "porrima"), ("porrima", "auva"), ("auva", "vindemiatrix"),
              ("porrima", "heze"), ("heze", "spica"), ("spica", "thetavir"), ("thetavir", "iotavir"),
              ("heze", "109vir")]),
    "libra": dict(cn="天秤座", en="LIBRA", sym="♎", dates="9.23 - 10.23", element="风象 · 守护星 金星", stars=[
        ("zubenelgenubi", 14.848, -16.04, 2.75, "氐宿一", "α"),
        ("zubeneschamali", 15.283, -9.38, 2.61, None, "β"),
        ("zubenelakrab", 15.592, -14.79, 3.91, None, "γ"),
        ("sigmalib", 15.068, -8.58, 3.29, None, "σ"),
    ], lines=[("zubenelgenubi", "zubeneschamali"), ("zubeneschamali", "sigmalib"), ("zubenelgenubi", "zubenelakrab")]),
    "scorpius": dict(cn="天蝎座", en="SCORPIUS", sym="♏", dates="10.24 - 11.22", element="水象 · 守护星 冥王星", stars=[
        ("antares", 16.490, -26.43, 1.06, "心宿二", "α Antares"),
        ("acrab", 16.091, -19.81, 2.62, None, "β"),
        ("dschubba", 16.006, -22.62, 2.29, None, "δ"),
        ("piscor", 15.981, -26.11, 2.89, None, "π"),
        ("rhoscor", 15.948, -29.21, 3.87, None, "ρ"),
        ("nuscor", 16.199, -19.47, 4.00, None, "ν"),
        ("sigscor", 16.352, -25.59, 2.88, None, "σ"),
        ("tauscor", 16.598, -28.22, 2.82, None, "τ"),
        ("epsscor", 16.836, -34.29, 2.29, None, "ε"),
        ("muscor", 16.864, -38.05, 3.00, None, "μ"),
        ("zetscor", 16.909, -42.36, 3.62, None, "ζ"),
        ("etascore", 17.202, -43.24, 3.33, None, "η"),
        ("thetscor", 17.622, -42.99, 3.62, None, "θ"),
        ("iotscor", 17.793, -40.13, 2.99, None, "ι"),
        ("shaula", 17.560, -37.10, 1.62, None, "λ Shaula"),
    ], lines=[("nuscor", "acrab"), ("acrab", "dschubba"), ("dschubba", "piscor"), ("piscor", "rhoscor"),
              ("dschubba", "sigscor"), ("sigscor", "antares"), ("antares", "tauscor"), ("tauscor", "epsscor"),
              ("epsscor", "muscor"), ("muscor", "zetscor"), ("zetscor", "etascore"), ("etascore", "thetscor"),
              ("thetscor", "iotscor"), ("iotscor", "shaula")]),
    "sagittarius": dict(cn="射手座", en="SAGITTARIUS", sym="♐", dates="11.23 - 12.21", element="火象 · 守护星 木星", stars=[
        ("kausaustralis", 18.403, -34.38, 1.79, "箕宿三", "ε"),
        ("kausmedia", 18.350, -29.83, 2.72, None, "δ"),
        ("kausborealis", 18.466, -25.42, 2.82, None, "λ"),
        ("nunki", 18.921, -26.30, 2.05, None, "σ Nunki"),
        ("ascella", 19.043, -29.88, 2.60, None, "ζ"),
        ("tausgr", 19.117, -27.67, 3.32, None, "τ"),
        ("alnasl", 18.096, -30.42, 2.99, None, "γ"),
        ("etassgr", 18.296, -36.76, 3.10, None, "η"),
        ("pissgr", 19.162, -21.02, 2.88, None, "π"),
    ], lines=[("alnasl", "kausmedia"), ("kausmedia", "kausborealis"), ("kausborealis", "nunki"),
              ("nunki", "pissgr"), ("nunki", "tausgr"), ("tausgr", "ascella"), ("ascella", "kausaustralis"),
              ("kausaustralis", "etassgr"), ("kausaustralis", "kausmedia")]),
    "capricornus": dict(cn="摩羯座", en="CAPRICORNUS", sym="♑", dates="12.22 - 1.19", element="土象 · 守护星 土星", stars=[
        ("algedi", 20.299, -12.55, 3.57, None, "α Algedi"),
        ("dabih", 20.350, -14.78, 3.08, None, "β Dabih"),
        ("nashira", 21.668, -16.66, 3.68, None, "γ"),
        ("denebalgedi", 21.784, -16.13, 2.87, "垒壁阵四", "δ"),
        ("zetcap", 21.443, -22.41, 3.68, None, "ζ"),
        ("thetcap", 21.099, -17.23, 4.07, None, "θ"),
        ("omegacap", 20.870, -26.92, 4.11, None, "ω"),
        ("psicap", 20.768, -25.26, 4.11, None, "ψ"),
    ], lines=[("algedi", "dabih"), ("dabih", "psicap"), ("psicap", "omegacap"), ("omegacap", "zetcap"),
              ("zetcap", "thetcap"), ("thetcap", "nashira"), ("nashira", "denebalgedi")]),
    "aquarius": dict(cn="水瓶座", en="AQUARIUS", sym="♒", dates="1.20 - 2.18", element="风象 · 守护星 天王星", stars=[
        ("sadalmelik", 22.096, -0.32, 2.94, None, "α"),
        ("sadalsuud", 21.526, -5.57, 2.90, "虚宿一", "β"),
        ("sadachbia", 22.360, -1.39, 3.84, None, "γ"),
        ("zetaaqr", 22.488, -0.02, 3.65, None, "ζ"),
        ("etaaqr", 22.589, -0.12, 4.02, None, "η"),
        ("piaqr", 23.372, 1.38, 4.66, None, "π"),
        ("epsaqr", 20.795, -9.50, 3.77, None, "ε"),
    ], lines=[("sadalsuud", "sadalmelik"), ("sadalmelik", "sadachbia"), ("sadachbia", "zetaaqr"),
              ("zetaaqr", "etaaqr"), ("etaaqr", "piaqr"), ("sadalsuud", "epsaqr")]),
    "pisces": dict(cn="双鱼座", en="PISCES", sym="♓", dates="2.19 - 3.20", element="水象 · 守护星 海王星", stars=[
        ("alrescha", 1.536, 2.76, 3.82, "外屏七", "α"),
        ("gammapsc", 1.567, 3.28, 3.69, None, "γ"),
        ("thetapsc", 1.753, 9.92, 4.28, None, "θ"),
        ("omegapsc", 23.988, 6.86, 4.01, None, "ω"),
        ("lambdapsc", 23.699, 1.78, 4.50, None, "λ"),
        ("betapsc", 23.066, 3.83, 4.53, None, "β"),
    ], lines=[("alrescha", "gammapsc"), ("gammapsc", "thetapsc"), ("thetapsc", "omegapsc"),
              ("omegapsc", "lambdapsc"), ("lambdapsc", "alrescha"), ("alrescha", "betapsc")]),
}

NEBULA_PALETTES = [
    [(86, 50, 150), (140, 60, 120), (40, 80, 140)],
    [(60, 60, 150), (120, 50, 140), (30, 90, 130)],
    [(90, 45, 130), (50, 90, 150), (130, 70, 100)],
]


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def project(stars):
    """球面 -> 平面（球心投影），返回 {id: (x, y)}（归一化坐标，后续缩放）"""
    ras = [s[1] * 15.0 for s in stars]
    decs = [s[2] for s in stars]
    # 中心：RA 用单位向量平均避免跨 0h 问题
    x = sum(math.cos(math.radians(r)) for r in ras) / len(ras)
    y = sum(math.sin(math.radians(r)) for r in ras) / len(ras)
    ra0 = math.degrees(math.atan2(y, x)) % 360.0
    dec0 = sum(decs) / len(decs)
    ra0r, dec0r = math.radians(ra0), math.radians(dec0)
    pts = {}
    for s in stars:
        ra, dec = math.radians(s[1] * 15.0), math.radians(s[2])
        dra = ra - ra0r
        cd = math.cos(dec)
        x_ = cd * math.sin(dra)
        y_ = math.cos(dec0r) * math.sin(dec) - math.sin(dec0r) * cd * math.cos(dra)
        pts[s[0]] = (x_, -y_)  # 天球习惯：北向上
    return pts


def draw_background(img):
    d = ImageDraw.Draw(img)
    top, bottom = (7, 10, 34), (24, 13, 44)
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
        d.line([(0, y), (W, y)], fill=c)


def draw_nebula(img, seed):
    rng = random.Random(seed)
    palette = NEBULA_PALETTES[seed % len(NEBULA_PALETTES)]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    for i in range(6):
        cx = rng.randint(60, W - 60)
        cy = rng.randint(240, H - 260)
        rx, ry = rng.randint(120, 300), rng.randint(90, 240)
        color = palette[i % len(palette)] + (rng.randint(26, 44),)
        dl.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(70))
    img.alpha_composite(layer)


def draw_field_stars(img, seed):
    rng = random.Random(seed * 7 + 3)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    for _ in range(330):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(0.4, 1.5)
        a = rng.randint(60, 210)
        tint = rng.choice([(255, 255, 255), (200, 215, 255), (255, 235, 210), (235, 240, 255)])
        dl.ellipse([x - r, y - r, x + r, y + r], fill=tint + (a,))
    for _ in range(18):  # 稍亮的背景星带微光
        x, y = rng.uniform(20, W - 20), rng.uniform(20, H - 20)
        r = rng.uniform(1.6, 2.6)
        dl.ellipse([x - r * 3, y - r * 3, x + r * 3, y + r * 3], fill=(190, 205, 255, 26))
        dl.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 230))
    img.alpha_composite(layer)


def fit_points(pts, box):
    xs = [p[0] for p in pts.values()]
    ys = [p[1] for p in pts.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    spanx = max(maxx - minx, 1e-6)
    spany = max(maxy - miny, 1e-6)
    bx0, by0, bx1, by1 = box
    scale = min((bx1 - bx0) / spanx, (by1 - by0) / spany)
    cx = (bx0 + bx1) / 2
    cy = (by0 + by1) / 2
    mx, my = (minx + maxx) / 2, (miny + maxy) / 2
    return {k: (cx + (v[0] - mx) * scale, cy + (v[1] - my) * scale) for k, v in pts.items()}


def draw_constellation(img, info, pts):
    stars = {s[0]: s for s in info["stars"]}
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    # 连线辉光（两层）
    for a, b in info["lines"]:
        p1, p2 = pts[a], pts[b]
        dl.line([p1, p2], fill=(110, 160, 255, 70), width=7)
    glow = layer.filter(ImageFilter.GaussianBlur(4))
    img.alpha_composite(glow)
    dl2 = ImageDraw.Draw(img)
    for a, b in info["lines"]:
        p1, p2 = pts[a], pts[b]
        dl2.line([p1, p2], fill=(195, 220, 255, 190), width=2)
    # 恒星
    brightest = min(s[3] for s in info["stars"])
    for sid, (px, py) in pts.items():
        s = stars[sid]
        mag = s[3]
        r = max(1.8, min(7.0, 8.2 - mag * 2.2))
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hd = ImageDraw.Draw(halo)
        hd.ellipse([px - r * 3, py - r * 3, px + r * 3, py + r * 3],
                   fill=(150, 180, 255, 60 if mag > brightest + 0.4 else 100))
        halo = halo.filter(ImageFilter.GaussianBlur(r * 1.2))
        img.alpha_composite(halo)
        dl2.ellipse([px - r, py - r, px + r, py + r], fill=(255, 255, 255, 245))
        # 最亮星加衍射十字光芒
        if mag <= brightest + 0.3:
            spike = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(spike)
            L = r * 5.5
            sd.line([px - L, py, px + L, py], fill=(255, 255, 255, 90), width=2)
            sd.line([px, py - L, px, py + L], fill=(255, 255, 255, 90), width=2)
            spike = spike.filter(ImageFilter.GaussianBlur(1.4))
            img.alpha_composite(spike)


def draw_star_labels(img, info, pts):
    d = ImageDraw.Draw(img)
    f_cn = _font(F_CN_BOLD, 30)
    f_en = _font(F_EN, 21)
    for s in info["stars"]:
        sid, _, _, _, cn, en = s
        if not cn and not en:
            continue
        px, py = pts[sid]
        lx, ly = px + 16, py - 14
        # 出界时换方向
        if lx > W - 190:
            lx = px - 16
            anchor = "ra"
        else:
            anchor = "la"
        if cn:
            d.text((lx + 1, ly + 1), cn, font=f_cn, fill=(10, 10, 30, 200), anchor=anchor)
            d.text((lx, ly), cn, font=f_cn, fill=(255, 217, 138, 255), anchor=anchor)
            ly += 34
        if en:
            d.text((lx + 1, ly + 1), en, font=f_en, fill=(10, 10, 30, 200), anchor=anchor)
            d.text((lx, ly), en, font=f_en, fill=(200, 208, 235, 220), anchor=anchor)


def draw_titles(img, info):
    d = ImageDraw.Draw(img)
    f_sym = _font(F_SYM, 88)
    f_cn = _font(F_CN_BOLD, 76)
    f_en = _font(F_EN, 30)
    f_meta = _font(F_CN, 30)
    f_small = _font(F_CN, 24)
    # 顶部：符号 + 名称
    sym = info["sym"]
    bbox = d.textbbox((0, 0), sym, font=f_sym)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 64), sym, font=f_sym, fill=(255, 224, 160, 255))
    cn = info["cn"]
    bbox = d.textbbox((0, 0), cn, font=f_cn)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 168), cn, font=f_cn, fill=(250, 246, 235, 255))
    en = info["en"]
    spaced = "  ".join(en)
    bbox = d.textbbox((0, 0), spaced, font=f_en)
    d.text(((W - (bbox[2] - bbox[0])) / 2, 262), spaced, font=f_en, fill=(170, 180, 220, 230))
    # 底部：日期 + 元素
    meta = info["dates"]
    bbox = d.textbbox((0, 0), meta, font=f_meta)
    d.text(((W - (bbox[2] - bbox[0])) / 2, H - 150), meta, font=f_meta, fill=(255, 224, 160, 240))
    elem = info["element"]
    bbox = d.textbbox((0, 0), elem, font=f_small)
    d.text(((W - (bbox[2] - bbox[0])) / 2, H - 104), elem, font=f_small, fill=(190, 198, 228, 220))
    tag = "✦  N . E . K . O  ✦"
    f_tag = _font(F_SYM, 24)  # Segoe UI Symbol 含 ✦ 字形，避免方块
    bbox = d.textbbox((0, 0), tag, font=f_tag)
    d.text(((W - (bbox[2] - bbox[0])) / 2, H - 60), tag, font=f_tag, fill=(140, 150, 190, 170))


def draw_vignette(img):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(120):  # 四周渐暗
        a = int(70 * (1 - i / 120) ** 1.6)
        d.rectangle([i, i, W - i, H - i], outline=(4, 4, 16, a))
    layer = layer.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(layer)


def render(key, info, index):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw_background(img)
    draw_nebula(img, index)
    draw_field_stars(img, index)
    pts = fit_points(project(info["stars"]), (120, 380, W - 120, H - 220))
    draw_constellation(img, info, pts)
    draw_star_labels(img, info, pts)
    draw_titles(img, info)
    draw_vignette(img)
    out = os.path.join(OUT_DIR, f"{key}.png")
    img.convert("RGB").save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for i, (key, info) in enumerate(ZODIAC.items()):
        path = render(key, info, i)
        size = os.path.getsize(path)
        print(f"OK {key}.png {size} bytes")
    print("ALL DONE")
