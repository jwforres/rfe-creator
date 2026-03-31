#!/usr/bin/env python3
"""State persistence for skills — survives context compression.

Usage:
    # Initialize config (creates tmp/ dir, overwrites file)
    python3 scripts/state.py init <file> key=value ...

    # Set/append key-value pairs to a config file
    python3 scripts/state.py set <file> key=value ...

    # Read a config or ID file (prints contents)
    python3 scripts/state.py read <file>

    # Write an ID list (one per line, overwrites)
    python3 scripts/state.py write-ids <file> <ID> [ID ...]

    # Read an ID list (prints space-separated on one line)
    python3 scripts/state.py read-ids <file>

    # Clean tmp/ directory
    python3 scripts/state.py clean
"""
import os
import sys


def cmd_init(args):
    """Create tmp/ and write a fresh config file with key=value pairs."""
    if len(args) < 1:
        print("Usage: state.py init <file> [key=value ...]", file=sys.stderr)
        sys.exit(1)
    path = args[0]
    os.makedirs(os.path.dirname(path) or "tmp", exist_ok=True)
    pairs = _parse_pairs(args[1:])
    with open(path, "w") as f:
        for k, v in pairs:
            f.write(f"{k}: {v}\n")


def cmd_set(args):
    """Append key-value pairs to an existing config file."""
    if len(args) < 2:
        print("Usage: state.py set <file> key=value ...", file=sys.stderr)
        sys.exit(1)
    path = args[0]
    pairs = _parse_pairs(args[1:])
    with open(path, "a") as f:
        for k, v in pairs:
            f.write(f"{k}: {v}\n")


def cmd_read(args):
    """Print contents of a file."""
    if len(args) < 1:
        print("Usage: state.py read <file>", file=sys.stderr)
        sys.exit(1)
    with open(args[0]) as f:
        print(f.read(), end="")


def cmd_write_ids(args):
    """Write IDs to a file, one per line."""
    if len(args) < 2:
        print("Usage: state.py write-ids <file> <ID> [ID ...]", file=sys.stderr)
        sys.exit(1)
    path = args[0]
    ids = args[1:]
    os.makedirs(os.path.dirname(path) or "tmp", exist_ok=True)
    with open(path, "w") as f:
        for id_ in ids:
            f.write(f"{id_}\n")


def cmd_read_ids(args):
    """Read IDs from a file, print space-separated."""
    if len(args) < 1:
        print("Usage: state.py read-ids <file>", file=sys.stderr)
        sys.exit(1)
    with open(args[0]) as f:
        ids = [line.strip() for line in f if line.strip()]
    print(" ".join(ids))


def cmd_clean(args):
    """Remove tmp/ directory."""
    import shutil
    if os.path.exists("tmp"):
        shutil.rmtree("tmp")
    os.makedirs("tmp", exist_ok=True)


def _parse_pairs(args):
    """Parse key=value arguments into (key, value) tuples."""
    pairs = []
    for arg in args:
        if "=" not in arg:
            print(f"Invalid key=value: {arg}", file=sys.stderr)
            sys.exit(1)
        k, v = arg.split("=", 1)
        pairs.append((k, v))
    return pairs


COMMANDS = {
    "init": cmd_init,
    "set": cmd_set,
    "read": cmd_read,
    "write-ids": cmd_write_ids,
    "read-ids": cmd_read_ids,
    "clean": cmd_clean,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Commands: {', '.join(COMMANDS)}", file=sys.stderr)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
