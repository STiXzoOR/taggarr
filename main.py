#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI."""

import argparse
import time

import taggarr
from taggarr.config import START_RUNNING, WRITE_MODE, RUN_INTERVAL_SECONDS


def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    parser.add_argument(
        '--write-mode', type=int, choices=[0, 1, 2],
        default=WRITE_MODE,
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
    opts = parser.parse_args()

    if START_RUNNING:
        taggarr.run_loop(opts)
    elif any(vars(opts).values()):
        taggarr.run(opts)
    else:
        # Idle mode - wait for external trigger
        while True:
            time.sleep(RUN_INTERVAL_SECONDS)


if __name__ == '__main__':
    main()
