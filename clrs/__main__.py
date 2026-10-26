"""Pattern: Facade. `python -m clrs` hands its arguments to the command line."""

import sys

from clrs.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
