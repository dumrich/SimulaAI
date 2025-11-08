# simplex_tileable.py
# Tileable 2D Simplex noise heightmap
# pip install pillow

import math
import random
from PIL import Image


class Simplex:
    def __init__(self, seed=None):
        if seed is not None:
            random.seed(seed)

        self.grad3 = [
            (1, 1), (-1, 1), (1, -1), (-1, -1),
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]
        p = list(range(256))
        random.shuffle(p)
        self.perm = p * 2

        self.F2 = 0.5 * (math.sqrt(3.0) - 1.0)
        self.G2 = (3.0 - math.sqrt(3.0)) / 6.0

    def noise2d(self, xin, yin):
        # Standard 2D Simplex noise in [-1, 1]
        s = (xin + yin) * self.F2
        i = math.floor(xin + s)
        j = math.floor(yin + s)

        t = (i + j) * self.G2
        X0 = i - t
        Y0 = j - t
        x0 = xin - X0
        y0 = yin - Y0

        if x0 > y0:
            i1, j1 = 1, 0
        else:
            i1, j1 = 0, 1

        x1 = x0 - i1 + self.G2
        y1 = y0 - j1 + self.G2
        x2 = x0 - 1.0 + 2.0 * self.G2
        y2 = y0 - 1.0 + 2.0 * self.G2

        ii = i & 255
        jj = j & 255
        gi0 = self.perm[ii + self.perm[jj]] % 8
        gi1 = self.perm[ii + i1 + self.perm[jj + j1]] % 8
        gi2 = self.perm[ii + 1 + self.perm[jj + 1]] % 8

        n0 = n1 = n2 = 0.0

        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0:
            t0 *= t0
            g = self.grad3[gi0]
            n0 = t0 * t0 * (g[0] * x0 + g[1] * y0)

        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0:
            t1 *= t1
            g = self.grad3[gi1]
            n1 = t1 * t1 * (g[0] * x1 + g[1] * y1)

        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0:
            t2 *= t2
            g = self.grad3[gi2]
            n2 = t2 * t2 * (g[0] * x2 + g[1] * y2)

        # Scale result (empirical factor)
        return 70.0 * (n0 + n1 + n2)


def tileable_simplex_2d(noise, x, y, period_x, period_y):
    """
    Tileable noise via 4-corner blending.

    period_x, period_y are in "noise space" units.
    The result is periodic with those periods.
    """
    # Normalize to [0,1] for blending weights
    u = x / period_x
    v = y / period_y

    # Four corners sampled with shifts equal to the period:
    n00 = noise(x,          y)
    n10 = noise(x - period_x, y)
    n01 = noise(x,          y - period_y)
    n11 = noise(x - period_x, y - period_y)

    # Bilinear blend between 4 tiles
    return (
        (1 - u) * (1 - v) * n00 +
        u       * (1 - v) * n10 +
        (1 - u) * v       * n01 +
        u       * v       * n11
    )


def generate_simplex_image(
    width=512,
    height=512,
    scale=80.0,
    octaves=4,
    persistence=0.5,
    lacunarity=2.0,
    seed=42,
    path="simplex_tile.png",
):
    """
    Generates a seamless/tileable simplex noise heightmap.

    When you repeat simplex_tile.png in a grid, edges line up cleanly.
    """
    simplex = Simplex(seed)
    img = Image.new("L", (width, height))
    pixels = img.load()

    # Choose tile period in noise space.
    # We match it to the scaled image size so 1 tile = this image.
    period_x = width / scale
    period_y = height / scale

    for py in range(height):
        for px in range(width):
            amp = 1.0
            freq = 1.0
            value = 0.0
            max_amp = 0.0

            # Map pixel to base noise-space coordinates
            # (so that one image spans exactly [0, period_x], [0, period_y])
            x = (px / (width - 1)) * period_x
            y = (py / (height - 1)) * period_y

            for _ in range(octaves):
                # Use tileable simplex at this octave
                n = tileable_simplex_2d(
                    simplex.noise2d,
                    x * freq,
                    y * freq,
                    period_x * freq,
                    period_y * freq,
                )

                value += n * amp
                max_amp += amp
                amp *= persistence
                freq *= lacunarity

            # Normalize: Simplex outputs roughly [-1,1] after scaling
            value /= max_amp
            # Map to [0,1]
            value = (value + 1.0) / 2.0
            gray = int(max(0, min(255, value * 255)))
            pixels[px, py] = gray

    img.save(path)
    print(f"Saved {path} (tileable simplex)")
