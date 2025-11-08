import argparse
from perlin_noise_gen import generate_perlin_image
from simplex_noise_gen import generate_simplex_image

def generate_heightmap(args):
    if args.type == "perlin":
        generate_perlin_image(
            width=args.size,
            height=args.size,
            scale=args.scale,
            octaves=args.octaves,
            persistence=args.persistence,
            lacunarity=args.lacunarity,
            seed=args.seed,
            path=args.out,
        )
    elif args.type == "simplex":
        generate_simplex_image(
            width=args.size,
            height=args.size,
            scale=args.scale,
            octaves=args.octaves,
            persistence=args.persistence,
            lacunarity=args.lacunarity,
            seed=args.seed,
            path=args.out,
        )
    else:
        raise ValueError("Unsupported noise type: {}".format(args.type))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates noise image based on parameters")
    parser.add_argument("--type", type=str, choices=["perlin", "simplex"], required=True, help="Type of noise to generate")
    parser.add_argument("--size", type=int, default=512, help="Specify the size of the noise image (nxn)")
    parser.add_argument("--out", type=str, required=True, help="File path for the outputted file")
    parser.add_argument("--scale", "-s", type=float, default=80.0, help="Scale represents how zoomed-out the heightmap is (higher == farther away == less noise)")
    parser.add_argument("--octaves", "-o", type=int, default=4, help="Number of layers of noise to apply")
    parser.add_argument("--persistence", "-p", type=float, default=0.5, help="Influence each successive octave has")
    parser.add_argument("--lacunarity", "-l", type=float, default=2.0, help="Speed at which frequency increases thorughout successive octaves")
    parser.add_argument("--seed", type=int, default=42, help="Seed for the random number generator")
    args = parser.parse_args()
    generate_heightmap(args)