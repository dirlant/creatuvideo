import sys, json, subprocess, os, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter
B = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FP = B + r"\_operacion\_work\Poppins-Bold.ttf"; FB = B + r"\_operacion\_work\Billabong.otf"; FE = r"C:\Windows\Fonts\seguiemj.ttf"
W, H = 1080, 1920
L, R, TOP = 60, 960, 190          # zona segura TikTok
FUCSIA = (214, 20, 128); WHITE = (255, 255, 255)
EM = re.compile("([\u2300-\u23FF\u2600-\u27BF\U0001F000-\U0001FAFF\u2B50\uFE0F]+)")
def toks(line):
    out = []
    for i, part in enumerate(line.split("*")):
        for r in EM.split(part):
            if not r: continue
            if EM.fullmatch(r): out.append((r, "e"))
            elif i % 2 and re.fullmatch(r"[a-z]+", r): out.append((r, "b"))              # palabra clave en Billabong (solo a-z)
            else: out.append((r.upper() if i % 2 else r, "p"))                           # con tilde o ñ: en Verdana, mayusculas
    return out
def fonts(sz): return {"p": ImageFont.truetype(FP, sz), "b": ImageFont.truetype(FB, int(sz*1.6)), "e": ImageFont.truetype(FE, sz)}
def width(line, sz):
    f = fonts(sz); return sum(f[k].getlength(t.lower() if k=="b" else t) for t, k in toks(line))
CAJA = True          # False: el titulo va sin fondo (solo letra con sombra)
CHIP_FUCSIA = False  # True: etiqueta del rubro en fucsia con letra blanca
def draw_line(td, line, sz, cx, y, color, stroke=0, solo_texto=False):
    f = fonts(sz); x = cx - width(line, sz)/2
    for t, k in toks(line):
        if k == "e":
            if not solo_texto: td.text((x, y), t, font=f["e"], embedded_color=True, anchor="ls")
        else:
            t = t.lower() if k == "b" else t
            td.text((x, y), t, font=f[k], fill=color+(255,), anchor="ls", stroke_width=stroke, stroke_fill=(0,0,0,255))
        x += f[k].getlength(t)
def render(lines, cat, out):
    sz = 42
    while max(width(l, sz) for l in lines) > 700 and sz > 26: sz -= 1
    cx = (L + R) / 2
    bx = tp = None
    box = Image.new("RGBA", (W,H), (0,0,0,0)); txt = Image.new("RGBA", (W,H), (0,0,0,0))
    bd, td = ImageDraw.Draw(box), ImageDraw.Draw(txt)
    # etiqueta de categoria (pildora blanca, texto fucsia)
    csz = max(int(sz*0.78), 22); cw = width(cat, csz); ch = int(csz*2.0); cpad = 24
    y = TOP
    bd.rounded_rectangle((cx-cw/2-cpad, y, cx+cw/2+cpad, y+ch), radius=ch//2, fill=(FUCSIA if CHIP_FUCSIA else WHITE)+(255,))
    draw_line(td, cat, csz, cx, y + int(ch*0.7), WHITE if CHIP_FUCSIA else FUCSIA)
    y += ch + 12
    if CAJA: bh = int(sz*1.95); gap = 8; bl = 0.69   # cajas fucsia: una por linea
    else:    bh = int(sz*1.4); gap = 0; bl = 0.8     # sin caja: interlineado compacto
    padx = 24; maxw = 0; rows = []
    tsh = Image.new("RGBA", (W,H), (0,0,0,0)); sd = ImageDraw.Draw(tsh)  # sombra del texto (titulo sin caja)
    for line in lines:
        w = width(line, sz); maxw = max(maxw, w)
        if CAJA:
            bd.rounded_rectangle((cx-w/2-padx, y, cx+w/2+padx, y+bh), radius=int(bh*0.28), fill=FUCSIA+(255,))
            draw_line(td, line, sz, cx, y + int(bh*bl), WHITE)
        else:
            draw_line(sd, line, sz, cx, y + int(bh*bl) + 4, (0,0,0), stroke=3, solo_texto=True)
            draw_line(td, line, sz, cx, y + int(bh*bl), WHITE, stroke=2)
        rows.append(y); y += bh + gap
    sy = rows[1] + int(bh*bl)
    for sx in (cx - maxw/2 - padx - sz*1.5, cx + maxw/2 + padx + sz*0.35):
        td.text((sx, sy), "\u2728", font=fonts(sz)["e"], embedded_color=True, anchor="ls")
    shadow = Image.new("RGBA", (W,H), (0,0,0,0)); shadow.paste((0,0,0,110), (0,0), box.split()[3].point(lambda a: a))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6)); shadow = ImageChops_offset(shadow, 0, 5)
    shadow.alpha_composite(tsh.filter(ImageFilter.GaussianBlur(5)))
    shadow.alpha_composite(box); shadow.alpha_composite(txt); shadow.save(out)
def ImageChops_offset(im, dx, dy):
    o = Image.new("RGBA", im.size, (0,0,0,0)); o.paste(im, (dx, dy)); return o
if __name__ == "__main__":
    j = json.load(open(sys.argv[1], encoding="utf-8-sig")); ff = j["ffmpeg"]
    only = sys.argv[2] if len(sys.argv) > 2 else None
    for it in j["items"]:
        if only and it["id"] != only: continue
        png = os.path.join(B, "_operacion", "_work", "ov_%s.png" % it["id"]); render(it["lines"], it["cat"], png)
        name = re.sub(r'[\\/:*?"<>|]', "", " ".join(it["lines"]).replace("*","")).strip().upper()
        out = os.path.join(B, "procesado", name + ".mp4")
        if os.environ.get("PREVIEW"): print("png", png); continue
        norm = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p"
        fc = ("[0:v]trim=0:6,setpts=PTS-STARTPTS,%s[h];[h][2:v]overlay=0:0:format=auto,format=yuv420p[v0];[0:a]atrim=0:6,asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=stereo[a0];"
              "[1:v]setpts=PTS-STARTPTS,%s[v1];[1:a]asetpts=PTS-STARTPTS,aresample=44100,aformat=channel_layouts=stereo[a1];"
              "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]") % (norm, norm)
        cmd = [ff,"-y","-v","error","-i",it["hook"],"-i",it["src"],"-i",png,"-filter_complex",fc,"-map","[v]","-map","[a]",
               "-c:v","libx264","-crf","20","-preset","medium","-c:a","aac","-b:a","160k","-movflags","+faststart",out]
        r = subprocess.run(cmd, capture_output=True, text=True)
        print(it["id"], "OK" if r.returncode==0 else r.stderr, it["cat"])

