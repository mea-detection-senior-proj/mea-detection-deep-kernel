"""Freeze embeddings/splits/evaluation draws before training or observing test scores."""
import argparse

from experiments.configuration import load_config
from experiments.locked import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(load_config(args.config), args.output)


if __name__ == "__main__":
    main()
