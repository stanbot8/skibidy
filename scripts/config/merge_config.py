#!/usr/bin/env python3
"""Merge bdm.core.toml with module configs into bdm.toml.

Reads bdm.core.toml (core tissue params, committed to git) and appends
each modules/*/config.toml file (sorted alphabetically) to produce bdm.toml
(gitignored runtime config that BioDynaMo reads).

Modules with `enabled = false` are skipped.

Usage:
    python3 scripts/config/merge_config.py                           # default paths
    python3 scripts/config/merge_config.py bdm.core.toml modules/    # explicit paths
"""

import glob
import os
import re
import sys


def is_module_enabled(path):
    """Check if a module TOML has enabled = true (or no enabled key)."""
    with open(path) as f:
        for line in f:
            stripped = line.split("#")[0].strip()
            if re.match(r"enabled\s*=\s*false", stripped):
                return False
            if re.match(r"enabled\s*=\s*true", stripped):
                return True
    # No enabled key found -- include by default
    return True


def merge(master_path="bdm.core.toml", modules_dir="modules",
          output_path="bdm.toml"):
    """Merge master config with enabled module configs."""
    if not os.path.isfile(master_path):
        print(f"Error: {master_path} not found.")
        sys.exit(1)

    with open(master_path) as f:
        master = f.read()

    # Auto-discover module configs (modules/*/config.toml layout)
    pattern = os.path.join(modules_dir, "*", "config.toml")
    module_files = sorted(glob.glob(pattern))

    if not module_files:
        print(f"Warning: no module configs found in {modules_dir}/")
        with open(output_path, "w") as f:
            f.write(master)
        return

    # Filter to enabled modules only (name = parent directory)
    enabled = [(p, os.path.basename(os.path.dirname(p))) for p in module_files
               if is_module_enabled(p)]
    skipped = [os.path.basename(os.path.dirname(p)) for p in module_files
               if not is_module_enabled(p)]

    # Append enabled module sections after master content
    parts = [master.rstrip()]
    for path, name in enabled:
        with open(path) as f:
            content = f.read().rstrip()
        parts.append(f"\n# ---- {name} ----")
        parts.append(content)

    merged = "\n".join(parts) + "\n"

    with open(output_path, "w") as f:
        f.write(merged)

    names = [n for _, n in enabled]
    msg = f"Merged {len(enabled)} modules: {', '.join(names)}"
    if skipped:
        msg += f" (skipped {len(skipped)} disabled: {', '.join(skipped)})"
    print(msg)


def main():
    master = sys.argv[1] if len(sys.argv) > 1 else "bdm.core.toml"
    modules_dir = sys.argv[2] if len(sys.argv) > 2 else "modules"
    output = sys.argv[3] if len(sys.argv) > 3 else "bdm.toml"
    merge(master, modules_dir, output)


if __name__ == "__main__":
    main()
