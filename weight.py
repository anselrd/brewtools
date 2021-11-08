import argparse

from units import Gravity, Mass, Volume


def parse_args():
    parser = argparse.ArgumentParser()
    _input = parser.add_mutually_exclusive_group()
    _input.add_argument('-m', '--mass')
    _input.add_argument('-v', '--volume')
    parser.add_argument('-g', '--specific_gravity',
                        type=Gravity.from_text,
                        default=Gravity.from_sg(0))
    parser.add_argument('-u', '--units',
                        help='Units of the unknown quantity to be shown')
    return parser.parse_args()


def main():
    args = parse_args()

    water_density_g_ml = 0.9998395
    density = water_density_g_ml * args.specific_gravity.specific_gravity

    if args.volume:
        volume = Volume.from_text(args.volume)
        volume_str = args.volume
        mass = Mass.of(density * volume.in_(Volume.Units.MILLILITERS), Mass.Units.GRAMS)
        mass_str = f'{mass.in_(Mass.prefixes.get(args.units, Mass.Units.KILOGRAMS)):.4g}' + (args.units or 'kg')
    else:
        mass = Mass.from_text(args.mass)
        mass_str = args.mass
        volume = Volume.of(mass.in_(Mass.Units.GRAMS) / density, Volume.Units.MILLILITERS)
        volume_str = f'{volume.in_(Volume.prefixes.get(args.units, Volume.Units.GALLONS)):.4g}' + (args.units or 'gal')

    print(
        f'Mass:   {mass_str}',
        f'Volume: {volume_str}',
        f'SG:     {args.specific_gravity}',
        sep='\n'
    )


if __name__ == '__main__':
    main()
