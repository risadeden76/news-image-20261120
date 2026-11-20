"""news-image-20261120: draw one 1024x1024 PNG summing up the world news of
Friday 20 November 2026. Pure standard library: a small raster canvas, a
hand-built 5x7 bitmap font, and a minimal PNG encoder. Deterministic: the
same bytes on every run. Writes to $MAKEFUN_OUTPUT_DIR/entry.png, else
/output/entry.png."""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---- palette ---------------------------------------------------------------
PAPER = (247, 242, 231)
INK = (20, 24, 34)
NAVY = (18, 38, 74)
NAVY_LT = (30, 58, 110)
GOLD = (201, 162, 39)
RED = (178, 39, 30)
TEAL = (14, 110, 110)
GREEN = (32, 110, 54)
ORANGE = (214, 110, 26)
SKY = (120, 170, 210)
WHITE = (255, 255, 255)
GREY = (90, 92, 100)
CARD = (255, 253, 247)

# ---- 5x7 bitmap font (rows are 5 bits, "#" = on) ---------------------------
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}

# ---- canvas ----------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def disc(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5)
            for xx in range(cx - dx, cx + dx + 1):
                self.set(xx, yy, c)

    def ring(self, cx, cy, r, t, c):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if r - t <= d <= r:
                    self.set(xx, yy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for s in range(steps + 1):
            x = round(x0 + dx * s / steps)
            y = round(y0 + dy * s / steps)
            for a in range(-(t // 2), t // 2 + 1):
                for b in range(-(t // 2), t // 2 + 1):
                    self.set(x + a, y + b, c)

    def tri(self, cx, top, half, hgt, c):
        for yy in range(top, top + hgt + 1):
            span = int(half * (yy - top) / max(hgt, 1))
            for xx in range(cx - span, cx + span + 1):
                self.set(xx, yy, c)

    def text(self, x, y, s, scale, color):
        s = s.upper()
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx - x

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_center(self, cx, y, s, scale, color):
        w = self.text_w(s, scale)
        self.text(cx - w // 2, y, s, scale, color)

    def wrap(self, s, scale, max_w):
        words = s.upper().split(" ")
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if self.text_w(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        return lines


def panel(cv, x, y, w, h, accent):
    cv.rect(x, y, w, h, CARD)
    cv.rect(x, y, w, 6, accent)
    cv.rect(x, y, 2, h, accent)
    cv.rect(x + w - 2, y, 2, h, accent)
    cv.rect(x, y + h - 2, w, 2, accent)


def story(cv, x, y, w, accent, title1, title2, sub):
    """Small panel: icon zone is drawn by the caller first; this writes the
    two title lines and the wrapped subline in the lower half."""
    tx = x + 24
    cv.text(tx, y + 128, title1, 3, INK)
    cv.text(tx, y + 156, title2, 3, INK)
    for j, ln in enumerate(cv.wrap(sub, 2, w - 48)):
        cv.text(tx, y + 188 + j * 18, ln, 2, GREY)


def draw():
    cv = Canvas(W, H, PAPER)

    # ---- masthead -----------------------------------------------------------
    cv.rect(0, 0, W, 148, NAVY)
    cv.rect(0, 148, W, 6, GOLD)
    cv.text_center(W // 2, 18, "THE WORLD IN ONE DAY", 5, GOLD)
    cv.text_center(W // 2, 62, "FRIDAY 20 NOVEMBER 2026", 7, WHITE)
    cv.text_center(W // 2, 118, "FIVE STORIES FROM AROUND THE GLOBE", 3, SKY)

    # ---- lead story: the Shenzhen summit ------------------------------------
    # panel 24,172,976x252
    panel(cv, 24, 172, 976, 252, RED)
    for i, (code, col) in enumerate(
            (("US", RED), ("CN", (200, 40, 40)), ("RU", NAVY_LT))):
        cx = 122 + i * 118
        cv.disc(cx, 298, 48, col)
        cv.ring(cx, 298, 48, 4, WHITE)
        cv.text_center(cx, 284, code, 4, WHITE)
    cv.text(430, 196, "TRUMP, XI AND PUTIN", 4, INK)
    cv.text(430, 232, "MEET IN SHENZHEN", 4, INK)
    cv.rect(430, 272, 540, 4, GOLD)
    for j, ln in enumerate(cv.wrap(
            "First-ever three-way summit: joint pledge on peace "
            "and nuclear arms control.", 2, 540)):
        cv.text(430, 292 + j * 20, ln, 2, INK)

    # ---- row 2: ICJ + cyclone ----------------------------------------------
    # panels y 444..668
    panel(cv, 24, 444, 478, 224, NAVY_LT)
    cv.line(263, 470, 263, 548, INK, 5)
    cv.line(208, 478, 318, 478, INK, 5)
    cv.line(208, 478, 188, 520, INK, 3)
    cv.line(208, 478, 228, 520, INK, 3)
    cv.tri(208, 520, 24, 18, NAVY_LT)
    cv.line(318, 478, 298, 520, INK, 3)
    cv.line(318, 478, 338, 520, INK, 3)
    cv.tri(318, 520, 24, 18, NAVY_LT)
    cv.rect(243, 548, 40, 8, INK)
    story(cv, 24, 444, 478, NAVY_LT,
          "WORLD COURT: MYANMAR", "GUILTY OF GENOCIDE",
          "ICJ rules 9-6: Myanmar committed genocide against the Rohingya.")

    panel(cv, 522, 444, 478, 224, TEAL)
    for r, col in ((46, TEAL), (34, SKY), (22, TEAL), (11, SKY)):
        cv.ring(761, 508, r, 4, col)
    cv.disc(761, 508, 8, TEAL)
    story(cv, 522, 444, 478, TEAL,
          "CYCLONE AKVAN HITS", "ODISHA COAST",
          "300,000 evacuated as the storm makes landfall in India.")

    # ---- row 3: Houthi strikes + Anthropic ---------------------------------
    # panels y 688..912
    panel(cv, 24, 688, 478, 224, ORANGE)
    for bx, bw, bh in ((60, 40, 60), (112, 30, 80), (156, 44, 48),
                       (214, 28, 70), (256, 36, 44)):
        cv.rect(bx, 800 - bh, bw, bh, NAVY_LT)
    cv.disc(420, 748, 22, ORANGE)
    for k in range(8):
        ang = k * math.pi / 4
        cv.line(420, 748, int(420 + 38 * math.cos(ang)),
                int(748 + 38 * math.sin(ang)), ORANGE, 3)
    story(cv, 24, 688, 478, ORANGE,
          "HOUTHI STRIKES HIT", "SAUDI ARABIA",
          "Four targets, incl. a Riyadh tower and the airport.")

    panel(cv, 522, 688, 478, 224, GREEN)
    pts = [(556, 792), (620, 764), (684, 774), (748, 742),
           (812, 720), (876, 706), (940, 700)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], GREEN, 6)
    cv.line(940, 700, 918, 700, GREEN, 6)
    cv.line(940, 700, 940, 722, GREEN, 6)
    story(cv, 522, 688, 478, GREEN,
          "ANTHROPIC SOARS ON", "NASDAQ DEBUT",
          "AI shares jump 17% to about $97 on first trading day.")

    # ---- footer --------------------------------------------------------------
    cv.rect(0, 972, W, 52, NAVY)
    cv.text_center(W // 2, 988, "20 NOVEMBER 2026 - THE DAY'S NEWS", 3, WHITE)
    return cv


def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw.extend(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    cv = draw()
    write_png(cv, os.path.join(out, "entry.png"))


if __name__ == "__main__":
    main()
