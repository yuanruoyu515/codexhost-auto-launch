#!/usr/bin/env python3
"""Remove the listener while keeping active Desktop sessions and local logs."""
import subprocess
import sys
import manage

if __name__ == "__main__":
    try:
        raise SystemExit(manage.main(["uninstall"]))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
