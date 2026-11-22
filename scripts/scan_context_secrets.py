#!/usr/bin/env python3
"""Keep the original command name for the context secret scan.

Run me when: you run the context secret scan with the old command name.
"""
import sys

from scan_secrets import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
