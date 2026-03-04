"""Generate placeholder PNG icons for the Chrome extension."""
import struct, zlib, os

ICON_DIR = os.path.join(os.path.dirname(__file__), "..", "public", "icons")
os.makedirs(ICON_DIR, exist_ok=True)

def make_png(size: int, path: str):
    w = h = size
    pixels = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b = 79, 70, 229  # Indigo
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                r, g, b = 99, 102, 241
            cx, cy = w // 2, h // 2
            radius = w * 0.3
            if (x - cx) ** 2 + (y - cy) ** 2 < radius ** 2:
                r, g, b = 228, 228, 239
            row.extend([r, g, b, 255])
        pixels.append(bytes([0] + row))
    raw = b"".join(pixels)

    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    idat = zlib.compress(raw, 9)

    with open(path, "wb") as f:
        f.write(sig)
        f.write(chunk(b"IHDR", ihdr))
        f.write(chunk(b"IDAT", idat))
        f.write(chunk(b"IEND", b""))
    print(f"  Created {path} ({os.path.getsize(path)} bytes)")

for s in (16, 48, 128):
    make_png(s, os.path.join(ICON_DIR, f"icon{s}.png"))
print("Done!")
