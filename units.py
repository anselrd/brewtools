import re
from enum import Enum
from functools import total_ordering


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

    @classmethod
    def from_text(cls, text, correction='u'):
        grav_regex = r'(?P<quantity>\d(\.\d+)?)(?P<correction>[c|u])?$'
        match = re.match(grav_regex, text.lower())
        if not match:
            raise ValueError(f'Gravity value {text} is not the correct format. '
                             f'Enter a number followed (optionally) by \'c\' for corrected '
                             f'or \'u\' for uncorrected. If neither is provided the default is'
                             f'to interpret the value as uncorrected')
        gravity_quantity = float(match.group('quantity'))
        gravity_correction = match.group('correction') or correction
        if gravity_quantity < 1.5:
            gravity = cls.from_sg(gravity_quantity)
        else:
            gravity = cls.from_brix(gravity_quantity)
        if gravity_correction == 'u':
            gravity = cls.from_sg(corrected(gravity.gravity_pts))
        return gravity

    @property
    def gravity_pts(self):
        return (self.specific_gravity - 1) * 1000

    @property
    def brix(self):
        return self.gravity_pts / 4


def corrected(x):
    return x/1.04


_LB_TO_G = 453.592


class Mass:

    class Units(Enum):
        MICROGRAMS = 1e-6
        MILLIGRAMS = 1e-3
        GRAMS = 1
        KILOGRAMS = 1e3
        MEGAGRAMS = 1e6
        POUNDS = _LB_TO_G
        OUNCES = _LB_TO_G / 12
        TONS = _LB_TO_G * 2000

    prefixes = {
        'ug': Units.MICROGRAMS,
        'mg': Units.MILLIGRAMS,
        'g': Units.GRAMS,
        'kg': Units.KILOGRAMS,
        'Mg': Units.MEGAGRAMS,
        'lb': Units.POUNDS,
        'oz': Units.OUNCES,
        'tons': Units.TONS
    }

    def __init__(self, grams):
        self.grams = grams

    def __add__(self, other):
        if type(other) != type(self):
            raise TypeError(f'Cannot add objects of type {type(other)} with objects of type {type(self)}')
        return Mass(self.grams + other.grams)

    def __sub__(self, other):
        if type(other) != type(self):
            raise TypeError(f'Cannot subtract objects of type {type(other)} from objects of type {type(self)}')
        return Mass(self.grams - other.grams)

    def __mul__(self, other):
        if type(other) not in [float, int]:
            raise TypeError(f'Cannot scale mass by non-numeric type {type(other)}')
        return Mass(self.grams * other)

    def __truediv__(self, other):
        if type(other) not in [float, int]:
            raise TypeError(f'Cannot scale mass by non-numeric type {type(other)}')
        return Mass(self.grams / other)

    @classmethod
    def from_text(cls, text):
        units = '|'.join(cls.prefixes)
        mass_finder = rf'(?P<quantity>(\d*\.)?\d+([eE][-\+]?\d+?)?)(?P<units>{units})'
        masses = [
            cls.of(float(mo.group('quantity')), cls.prefixes[mo.group('units')])
            for mo in re.finditer(mass_finder, text)
        ]
        if not masses:
            raise ValueError(f'Unable to parse Mass string {text}')
        return sum(masses, Mass(0))

    @classmethod
    def of(cls, quantity: float, unit: Units):
        return cls(quantity * unit.value)

    def in_(self, unit: 'Mass.Units'):
        return self.grams / unit.value


_GAL_TO_L = 3.78541


class Volume:

    class Units(Enum):
        MILLILITERS = 1e-3
        LITERS = 1
        KILOLITERS = 1e3
        GALLONS = _GAL_TO_L
        QUARTS = _GAL_TO_L / 4
        PINTS = _GAL_TO_L / 4 / 2
        CUPS = _GAL_TO_L / 4 / 2 / 2
        OUNCES = _GAL_TO_L / 4 / 2 / 2 / 8

    prefixes = {
        'ml': Units.MILLILITERS,
        'l': Units.LITERS,
        'kl': Units.KILOLITERS,
        'g': Units.GALLONS,
        'gal': Units.GALLONS,
        'q': Units.QUARTS,
        'p': Units.PINTS,
        'c': Units.CUPS,
        'oz': Units.OUNCES,
        'floz': Units.OUNCES
    }

    def __init__(self, liters):
        self.liters = liters

    def __add__(self, other):
        if type(other) != type(self):
            raise TypeError(f'Cannot add objects of type {type(other)} with objects of type {type(self)}')
        return Volume(self.liters + other.liters)

    def __sub__(self, other):
        if type(other) != type(self):
            raise TypeError(f'Cannot subtract objects of type {type(other)} from objects of type {type(self)}')
        return Volume(self.liters - other.liters)

    def __mul__(self, other):
        if type(other) not in [float, int]:
            raise TypeError(f'Cannot scale volume by non-numeric type {type(other)}')
        return Volume(self.liters * other)

    def __truediv__(self, other):
        if type(other) not in [float, int]:
            raise TypeError(f'Cannot scale volume by non-numeric type {type(other)}')
        return Volume(self.liters / other)

    @classmethod
    def from_text(cls, text):
        units = '|'.join(cls.prefixes)
        volume_finder = rf'(?P<quantity>(\d*\.)?\d+([eE][-\+]?\d+?)?)(?P<units>{units})'
        # volumes = [
        #     cls.of(float(mo.group('quantity')), cls.prefixes[mo.group('units')])
        #     for mo in re.finditer(volume_finder, text)
        # ]
        volumes = []
        for mo in re.finditer(volume_finder, text):
            q = float(mo.group('quantity'))
            u = cls.prefixes[mo.group('units')]
            volumes.append(cls.of(q, u))
        if not volumes:
            raise ValueError(f'Unable to parse Volume string {text}')
        return sum(volumes, Volume(0))

    @classmethod
    def of(cls, quantity: float, unit: Units):
        return cls(quantity * unit.value)

    def in_(self, unit):
        return self.liters / unit.value
