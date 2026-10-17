"""``elicit`` command-line entry point."""

from __future__ import annotations

import sys


def main() -> int:
    from cli import main as _main

    return _main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
