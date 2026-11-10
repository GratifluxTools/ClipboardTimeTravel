"""アプリアイコンを生成する。
- assets/icon.png : exe のアイコン（flet build が読み込む）
- icon_data.py    : システムトレイ用に埋め込んだ同じ画像
独自のアイコンにする場合は、assets/icon.png を 256x256 以上の PNG に差し替えてから
`python tools/make_icon.py --from-png assets/icon.png` を実行すると icon_data.py を作り直せる。"""
import base64
import math
import os
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 256


def write_png(path, w, h, rgba: bytes) -> None:
    raw = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def seg_dist(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def render(size: int = SIZE) -> bytes:
    c = size / 2
    r_corner = size * 0.20
    ring_r, ring_w = size * 0.36, size * 0.055
    hand_w = size * 0.06
    bg, fg = (37, 99, 235, 255), (255, 255, 255, 255)
    out = bytearray(size * size * 4)
    for y in range(size):
        for x in range(size):
            px, py = x + 0.5, y + 0.5
            qx = abs(px - c) - (c - r_corner)
            qy = abs(py - c) - (c - r_corner)
            sdf = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r_corner
            i = (y * size + x) * 4
            if sdf > 0:
                continue  # 透明
            d_center = math.hypot(px - c, py - c)
            on_ring = abs(d_center - ring_r) <= ring_w / 2
            on_hour = seg_dist(px, py, c, c, c, c - size * 0.22) <= hand_w / 2
            on_minute = seg_dist(px, py, c, c, c + size * 0.20, c + size * 0.12) <= hand_w * 0.85 / 2
            on_dot = d_center <= size * 0.05
            color = fg if (on_ring or on_hour or on_minute or on_dot) else bg
            out[i:i + 4] = bytes(color)
    return bytes(out)


def write_icon_data(png_path: str) -> None:
    with open(png_path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    data_path = os.path.join(ROOT, "icon_data.py")
    with open(data_path, "w", encoding="utf-8") as fh:
        fh.write('"""トレイ用のアプリアイコン（tools/make_icon.py で生成）"""\n')
        fh.write(f'ICON_PNG_B64 = "{b64}"\n')
    print("wrote", data_path)


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    icon_png = os.path.join(ROOT, "assets", "icon.png")
    if "--from-png" in sys.argv:
        src = sys.argv[sys.argv.index("--from-png") + 1]
        with open(src, "rb") as fh:
            data = fh.read()
        with open(icon_png, "wb") as fh:
            fh.write(data)
    else:
        write_png(icon_png, SIZE, SIZE, render(SIZE))
        print("wrote", icon_png)
    write_icon_data(icon_png)
