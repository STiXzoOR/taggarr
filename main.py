#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI."""

import argparse
import sys
import time

import taggarr
from taggarr.config_loader import load_config, ConfigError


def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    parser.add_argument(
        '--config', '-c',
        help="Path to config file (default: searches standard locations)"
    )
    parser.add_argument(
        '--instances', '-i',
        help="Comma-separated list of instances to process (default: all)"
    )
    parser.add_argument(
        '--write-mode', type=int, choices=[0, 1, 2],
        default=0,
        help="0=default, 1=rewrite all, 2=remove all"
    )
    parser.add_argument(
        '--quick', action='store_true',
        help="Scan only first episode per season"
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="No API calls or file edits"
    )
    parser.add_argument(
        '--loop', action='store_true',
        help="Run continuously at configured interval"
    )
    opts = parser.parse_args()

    # Load configuration
    try:
        config = load_config(opts.config)
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run
    if opts.loop:
        taggarr.run_loop(opts, config)
    else:
        taggarr.run(opts, config)


if __name__ == '__main__':
    main()
