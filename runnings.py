import argparse
import sys
from collections import namedtuple
from itertools import accumulate
from operator import attrgetter

import inflect

from units import Gravity


WortData = namedtuple('WortData', ['volume', 'gravity'])


def gravityinputparser(g):
    return Gravity.from_text(g, correction='c')


def wortinputparser(ssv):
    try:
        volume, gravity = ssv.split('/')
    except ValueError:
        raise ValueError('Wort data should be entered in the format <volume>/<gravity>. '
                         'See the help text for more detail')
    try:
        volume = float(volume)
    except ValueError:
        raise ValueError(f'Entered volume {volume} was not a numeric value. Please enter the numeric value in gallons.')

    return WortData(volume, Gravity.from_text(gravity))


def validate(args):
    boiloff = args.boiloff_rate * args.boil_duration / 60
    shrinkage_factor = 1 - args.shrinkage_pct / 100
    if args.preboil_volume and args.final_volume:
        if (args.preboil_volume - boiloff) * shrinkage_factor != args.final_volume:
            raise ValueError(f'Pre-boil and final volumes both supplied but do not agree with boiloff/shrinkage')
    elif args.preboil_volume:
        args.final_volume = (args.preboil_volume - boiloff) * shrinkage_factor
    elif args.final_volume:
        args.preboil_volume = args.final_volume / shrinkage_factor + boiloff
    else:
        raise ValueError('At least one of \'-p/--preboil_volume\' or \'-f/--final_volume\' must be supplied')


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--runnings', type=wortinputparser, nargs='+', required=True,
                        help='Enter a list of runnings data in the format <volume [gal]>/<gravity>. '
                             'The volume is simply a numeric quantity of gallons for the running. '
                             'The gravity is a numeric quantity of either specific gravity or Brix, the units of which '
                             'are determined automatically (values less than 1.5 are considered specific gravities). '
                             'Optionally, if you have already corrected your refractometer measurement with a wort '
                             'correction factor, add a \'c\' to indicate that correction has already taken place. '
                             'Otherwise you may optionally supply a \'u\' to indicate an uncorrected measurement, but '
                             'this would be assumed and is not necessary. For example, if I took first runnings at 3 '
                             'gallons and measured 18 brix, then took second runnings at 2 gallons and measured 12.5 '
                             'brix, I would supply `-w 3/18 2/12.5`')
    parser.add_argument('-o', '--target_OG', type=gravityinputparser, required=True)
    parser.add_argument('-p', '--preboil_volume', type=float, help='Pre-boil volume in gallons')
    parser.add_argument('-f', '--final_volume', type=float, help='Cooled post-boil volume in gallons')
    parser.add_argument('-r', '--boiloff_rate', type=float, default=0.785, help='Boil-off rate in gallons/hour')
    parser.add_argument('-d', '--boil_duration', type=float, default=60, help='Boil time in minutes')
    parser.add_argument('-s', '--shrinkage_pct', type=float, default=4, help='Cooling shrinkage expressed as a percent')
    parser.add_argument('-u', '--unsorted', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    validate(args)

    return args


def main():
    args = parse_args()
    if not args.unsorted:
        args.runnings.sort(key=attrgetter('gravity'), reverse=True)

    preboil_gravity = Gravity.from_sg(args.target_OG.gravity_pts * args.final_volume / args.preboil_volume)

    total_sugars = [0] + list(accumulate([w.gravity.gravity_pts * w.volume for w in args.runnings]))
    total_volumes = [0] + list(accumulate([w.volume for w in args.runnings]))
    needed_sugar = args.target_OG.gravity_pts * args.final_volume

    # Check for issues with running gravities
    if total_sugars[-1] < needed_sugar:
        # Having not enough total sugar limits the final batch size
        batch_size = total_sugars[-1]/args.target_OG.gravity_pts
        sys.exit(f'Not enough sugar was extracted during the mash. Max batch size is {batch_size:.2f}gal '
                 f'(specified {args.final_volume:.2f}gal batch)')

    last_running = total_sugars.index(next(filter(lambda t: t >= needed_sugar, total_sugars))) - 1
    last_running_fraction = (needed_sugar - total_sugars[last_running]) / \
                            (total_sugars[last_running + 1] - total_sugars[last_running])
    last_running_volume = last_running_fraction * args.runnings[last_running].volume
    running_volume = total_volumes[last_running] + last_running_volume

    if running_volume > args.preboil_volume:
        excess_volume = running_volume - args.preboil_volume
        extra_boil = excess_volume / args.boiloff_rate * 60
        new_boil = args.boil_duration + extra_boil
        sys.exit(f'Boil time must be increased by {extra_boil:.1f} min ({new_boil:.2f} min boil).')

    volumes = [w.volume for w in args.runnings[:last_running]] + [last_running_volume]
    topoff_water = args.preboil_volume - sum(volumes)

    for i, v in enumerate(volumes):
        n = i + 1
        print(inflect.engine().ordinal(n), f'runnings: {v:.3f} gallons')

    print(f'Topoff water: {topoff_water:.3f} gallons')

    boiloff = args.boiloff_rate * args.boil_duration / 60
    shrinkage = 1 - args.shrinkage_pct / 100
    if args.preboil_volume:
        preboil_volume = args.preboil_volume
        final_volume = (args.preboil_volume - boiloff) * shrinkage
    else:
        preboil_volume = args.final_volme / shrinkage + boiloff
        final_volume = args.final_volume
    print('')
    print(f'Boil start: {preboil_volume:.2f}gal @ {preboil_gravity.specific_gravity:.3f}')
    print(f'Boil end: {final_volume:.2f}gal @ {args.target_OG.specific_gravity:.3f}')


if __name__ == '__main__':
    main()
