"""Make `python -m clausewitz` work, not just `python -m clausewitz.cli`.

The shorter form is what a reader types first. Without this file it fails with
"'clausewitz' is a package and cannot be directly executed", which reads like a
broken project rather than a wrong command -- and the person who hits it is
someone evaluating whether this repo is worth five more minutes.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
