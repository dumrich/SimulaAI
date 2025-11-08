# perlin_cpu.py
# Pure Python Perlin noise (2D) + image output
# Requires: Pillow  (pip install pillow)

import math
import random
from PIL import Image


class Perlin:
    def __init__(self, seed=None, repeat=-1):
        if seed is not None:
            random.seed(seed)
        self.repeat = repeat

        # Permutation table
        p = list(range(256))
        random.shuffle(p)
        self.p = p * 2  # repeat for overflow

    @staticmethod
    def fade(t):
        # 6t^5 - 15t^4 + 10t^3
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def lerp(a, b, t):
        return a + t * (b - a)

    @staticmethod
    def grad(hash, x, y):
        # Simple 2D gradient based on hash
        h = hash & 3
        if h == 0:
            return x + y
        if h == 1:
            return -x + y
        if h == 2:
            return x - y
        return -x - y

    def inc(self, n):
        n += 1
        if self.repeat > 0:
            n %= self.repeat
        return n

    def noise(self, x, y=0.0):
        # Optional tiling
        if self.repeat > 0:
            x = x % self.repeat
            y = y % self.repeat

        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255

        xf = x - math.floor(x)
        yf = y - math.floor(y)

        u = self.fade(xf)
        v = self.fade(yf)

        aa = self.p[self.p[xi] + yi]
        ab = self.p[self.p[xi] + self.inc(yi)]
        ba = self.p[self.p[self.inc(xi)] + yi]
        bb = self.p[self.p[self.inc(xi)] + self.inc(yi)]

        x1 = self.lerp(self.grad(aa, xf, yf),
                       self.grad(ba, xf - 1, yf), u)
        x2 = self.lerp(self.grad(ab, xf, yf - 1),
                       self.grad(bb, xf - 1, yf - 1), u)
        value = self.lerp(x1, x2, v)

        # Map from [-1, 1] to [0, 1]
        return (value + 1.0) / 2.0


def generate_perlin_image(
    width=512,
    height=512,
    scale=80.0,
    octaves=4,
    persistence=0.5,
    lacunarity=2.0,
    seed=42,
    path="perlin.png",
):
    perlin = Perlin(seed)
    img = Image.new("L", (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            amplitude = 1.0
            frequency = 1.0
            value = 0.0
            max_amp = 0.0

            # Fractal Brownian Motion (fBM): combine octaves
            for _ in range(octaves):
                sx = (x / scale) * frequency
                sy = (y / scale) * frequency

                value += perlin.noise(sx, sy) * amplitude
                max_amp += amplitude

                amplitude *= persistence
                frequency *= lacunarity

            value /= max_amp  # normalize to [0,1]
            gray = int(max(0, min(255, value * 255)))
            pixels[x, y] = gray

    img.save(path)
    print(f"Saved {path}")