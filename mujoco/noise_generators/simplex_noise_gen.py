# simplex_cpu.py
# Pure Python 2D Simplex noise + image generation
# Requires: Pillow  (pip install pillow)
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
        # Skew coordinates
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

        # Corner 0
        t0 = 0.5 - x0 * x0 - y0 * y0
        if t0 >= 0:
            t0 *= t0
            g = self.grad3[gi0]
            n0 = t0 * t0 * (g[0] * x0 + g[1] * y0)

        # Corner 1
        t1 = 0.5 - x1 * x1 - y1 * y1
        if t1 >= 0:
            t1 *= t1
            g = self.grad3[gi1]
            n1 = t1 * t1 * (g[0] * x1 + g[1] * y1)

        # Corner 2
        t2 = 0.5 - x2 * x2 - y2 * y2
        if t2 >= 0:
            t2 *= t2
            g = self.grad3[gi2]
            n2 = t2 * t2 * (g[0] * x2 + g[1] * y2)

        # Scale result to roughly [-1, 1]
        return 70.0 * (n0 + n1 + n2)

def generate_simplex_image(
    width=512,
    height=512,
    scale=80.0,
    octaves=4,
    persistence=0.5,
    lacunarity=2.0,
    seed=42,
    path="simplex.png",
):
    """
    Generate a simplex heightmap file for height field

    Args:
        width (int): width of the image
        height (int): height of the image
        scale (float): noisiness of the heightmap (smaller = more noisy)
        octaves (int): number of "layers" of noise blended together (higher = more structured)
        persistence (float): influence each successive octave has (smaller = smoother)
        lacunarity (float): speed at which frequency increases per octave (higher = more chaotic)
        seed (int): seed of the random number generator
        path (str): output file path
    """

    simplex = Simplex(seed)
    img = Image.new("L", (width, height))
    pixels = img.load()

    for y in range(height):
        for x in range(width):
            amplitude = 1.0
            frequency = 1.0
            value = 0.0
            max_amp = 0.0

            for _ in range(octaves):
                nx = (x / scale) * frequency
                ny = (y / scale) * frequency

                value += simplex.noise2d(nx, ny) * amplitude
                max_amp += amplitude
                amplitude *= persistence
                frequency *= lacunarity

            value /= max_amp
            value = (value + 1.0) / 2.0  # map to [0,1]
            gray = int(max(0, min(255, value * 255)))
            pixels[x, y] = gray

    img.save(path)
    print(f"Saved {path}")
