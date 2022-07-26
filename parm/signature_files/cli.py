import argparse

from parm.signature_files.sig_files import match_signature_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('target')
    parser.add_argument('-s', '--signatures', default='.')
    parser.add_argument('-o', '--output', default=None)
    args = parser.parse_args()

    match_signature_files(args.target, args.signatures, args.output)
