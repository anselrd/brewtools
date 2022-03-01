import argparse

from units import Mass


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--quoted_alpha', type=float)
    parser.add_argument('-o', '--obtained_alpha', type=float)
    parser.add_argument('-w', '--weight', type=Mass.from_text)
    parser.add_argument('-b', '--hop_basket', action='store_true')
    return parser.parse_args()


def main(args):
    quoted_alpha = args.quoted_alpha / 100 if args.quoted_alpha > 1 else args.quoted_alpha
    obtained_alpha = args.obtained_alpha / 100 if args.obtained_alpha > 1 else args.obtained_alpha

    basket_factor = 0.9 ** (-1) if args.hop_basket else 1
    new_weight: Mass = args.weight * basket_factor * quoted_alpha / obtained_alpha

    print(f'{new_weight.in_(Mass.Units.OUNCES):.02f}oz')


if __name__ == '__main__':
    main(parse_args())
