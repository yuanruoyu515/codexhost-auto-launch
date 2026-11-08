#!/usr/bin/env python3
"""Install CodexHost Auto Launch for the current user."""
import subprocess
import sys
import manage

if __name__ == "__main__":
    try:
        raise SystemExit(manage.main(["install", *sys.argv[1:]]))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
