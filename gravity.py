import argparse
import re
from collections import namedtuple
from functools import total_ordering
from itertools import accumulate
from operator import attrgetter

import inflect

WortData = namedtuple('WortData', ['volume', 'gravity'])


@total_ordering
class Gravity:
    def __init__(self, gravity):
        self.specific_gravity = 1 + gravity/1000

    def __repr__(self):
        return f'{self.specific_gravity:.06}'

    def __lt__(self, other):
        if type(other) is not type(self):
            raise TypeError(f'Cannot compare type {type(other)} to Gravity')
        return self.specific_gravity < other.specific_gravity

    def __eq__(self, other):
        if type(other) is not type(self):
            raise TypeError(f'Cannot compare type {type(other)} to Gravity')
        return self.specific_gravity == other.specific_gravity

    @classmethod
    def from_brix(cls, b):
        return cls(b*4)

    @classmethod
    def from_sg(cls, sg):
        return cls((sg - 1) * 1000 if 1 < sg < 1.2 else sg)

    @property
    def gravity_pts(self):
        return (self.specific_gravity - 1) * 1000

    @property
    def brix(self):
        return self.gravity_pts / 4


def corrected(x):
    return x/1.04


def readinginputparser(g, correction='u'):
    grav_regex = r'(?P<quantity>\d(\.\d+)?)(?P<correction>[c|u])?$'
    match = re.match(grav_regex, g.lower())
    if not match:
        raise ValueError(f'Gravity value {g} is not the correct format. '
                         f'Enter a number followed (optionally) by \'c\' for corrected '
                         f'or \'u\' for uncorrected. If neither is provided the default is'
                         f'to interpret the value as uncorrected')
    gravity_quantity = float(match.group('quantity'))
    gravity_correction = match.group('correction') or correction
    if gravity_quantity < 1.5:
        gravity = Gravity.from_sg(gravity_quantity)
    else:
        gravity = Gravity.from_brix(gravity_quantity)
    if gravity_correction == 'u':
        gravity = Gravity.from_sg(corrected(gravity.gravity_pts))
    return gravity


def gravityinputparser(g):
    return readinginputparser(g, correction='c')


def wortinputparser(ssv):
    volume, gravity = ssv.split('/')
    return WortData(float(volume), readinginputparser(gravity))


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
    parser.add_argument('-w', '--runnings', type=wortinputparser, nargs='+', required=True)
    parser.add_argument('-o', '--target_OG', type=gravityinputparser, required=True)
    parser.add_argument('-p', '--preboil_volume', type=float, help='Pre-boil volume in gallons')
    parser.add_argument('-s', '--postboil_volume', type=float, help='Post-boil volume in gallons')
    parser.add_argument('-r', '--boiloff_rate', type=float, default=1.7, help='Boil-off rate in gallons/hour')
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
        raise ValueError(f'Max possible gravity {Gravity.from_sg(total_gravities[-1]/args.postboil_volume)} '
                         f'is below target gravity {args.target_OG}')

    last_running_gravity = next(
        filter(
            lambda t: Gravity.from_sg(t/args.preboil_volume) > preboil_gravity,
            total_gravities
        )
    )
    last_running = total_gravities.index(last_running_gravity)
    u = (preboil_gravity.gravity_pts * args.preboil_volume - total_gravities[last_running-1]) / \
        args.runnings[last_running-1].gravity.gravity_pts
    volumes = [w.volume for w in args.runnings[:last_running-1]] + \
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