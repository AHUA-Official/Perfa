#!/usr/bin/env python3
from runner import main


if __name__ == "__main__":
    import sys
    sys.argv = [sys.argv[0], "--case-id", "cpu_focus_basic", *sys.argv[1:]]
    raise SystemExit(main())
