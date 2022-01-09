import argparse
import re
from collections import namedtuple
from itertools import accumulate
from operator import attrgetter

import inflect

from units import Gravity, corrected


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
    if args.preboil_volume and args.postboil_volume:
        if args.preboil_volume - boiloff != args.postboil_volume:
            raise ValueError(f'Pre and post boil volumes both supplied but do not agree with boiloff')
    elif args.preboil_volume:
        args.postboil_volume = args.preboil_volume - boiloff
    elif args.postboil_volume:
        args.preboil_volume = args.postboil_volume + boiloff
    else:
        raise ValueError('At least one of \'--preboil_volume\' or \'--postboil_volume\' must be supplied')


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
    parser.add_argument('-s', '--postboil_volume', type=float, help='Post-boil volume in gallons')
    parser.add_argument('-r', '--boiloff_rate', type=float, default=0.785, help='Boil-off rate in gallons/hour')
    parser.add_argument('-d', '--boil_duration', type=float, default=60, help='Boil time in minutes')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    validate(args)

    return args


def main():
    args = parse_args()
    args.runnings.sort(key=attrgetter('gravity'), reverse=True)

    preboil_gravity = Gravity.from_sg(args.target_OG.gravity_pts * args.postboil_volume / args.preboil_volume)

    total_gravities = [0] + list(accumulate([w.gravity.gravity_pts * w.volume for w in args.runnings]))
    max_gravity = Gravity.from_sg(total_gravities[-1] / args.preboil_volume)

    # Ensure there is enough sugar
    if max_gravity < preboil_gravity:
        raise ValueError(f'Max possible gravity {Gravity.from_sg(total_gravities[-1] / args.postboil_volume)} '
                         f'is below target gravity {args.target_OG}')

    last_running_gravity = next(
        filter(
            lambda t: Gravity.from_sg(t / args.preboil_volume) > preboil_gravity,
            total_gravities
        )
    )
    last_running = total_gravities.index(last_running_gravity)
    u = (preboil_gravity.gravity_pts * args.preboil_volume - total_gravities[last_running - 1]) / \
        args.runnings[last_running - 1].gravity.gravity_pts
    volumes = [w.volume for w in args.runnings[:last_running - 1]] + \
              [u] + \
              [0 for _ in range(len(args.runnings) - last_running)]

    for i, v in enumerate(filter(None, volumes)):
        n = i + 1
        print(inflect.engine().ordinal(n), f'runnings: {v:.3f} gallons')

    water_volume = args.preboil_volume - sum(volumes)
    if water_volume > 0:
        print(f'Topoff water: {water_volume:.3f} gallons')


if __name__ == '__main__':
    main()
