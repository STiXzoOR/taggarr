#!/usr/bin/env python3
"""Taggarr - Dub Analysis & Tagging CLI."""

import argparse
import sys
from pathlib import Path

import taggarr
from taggarr.config_loader import load_config, ConfigError


def main():
    parser = argparse.ArgumentParser(description=taggarr.__description__)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Scan command (default behavior)
    scan_parser = subparsers.add_parser("scan", help="Scan media libraries")
    scan_parser.add_argument(
        '--config', '-c',
        help="Path to config file (default: searches standard locations)"
    )
    scan_parser.add_argument(
        '--instances', '-i',
        help="Comma-separated list of instances to process (default: all)"
    )
    scan_parser.add_argument(
        '--write-mode', type=int, choices=[0, 1, 2],
        default=0,
        help="0=default, 1=rewrite all, 2=remove all"
    )
    scan_parser.add_argument(
        '--quick', action='store_true',
        help="Scan only first episode per season"
    )
    scan_parser.add_argument(
        '--dry-run', action='store_true',
        help="No API calls or file edits"
    )
    scan_parser.add_argument(
        '--loop', action='store_true',
        help="Run continuously at configured interval"
    )

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the web UI server")
    serve_parser.add_argument(
        '--host', default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    serve_parser.add_argument(
        '--port', type=int, default=8080,
        help="Port to listen on (default: 8080)"
    )
    serve_parser.add_argument(
        '--base-url', default="/",
        help="Base URL for reverse proxy (default: /)"
    )
    serve_parser.add_argument(
        '--db', type=str, default=None,
        help="Database path (default: ./taggarr.db)"
    )
    serve_parser.add_argument(
        '--reload', action='store_true',
        help="Enable auto-reload for development"
    )

    # For backwards compatibility, also support legacy args directly on parser
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

    if opts.command == "serve":
        _run_serve(opts)
    else:
        # Default to scan behavior (for backwards compatibility)
        _run_scan(opts)


def _run_scan(opts):
    """Run the scan command."""
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


def _run_serve(opts):
    """Run the serve command."""
    from taggarr.server import run_server

    db_path = Path(opts.db) if opts.db else None
    run_server(
        host=opts.host,
        port=opts.port,
        base_url=opts.base_url,
        db_path=db_path,
        reload=opts.reload,
    )


if __name__ == '__main__':
    main()
