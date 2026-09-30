#!/usr/bin/env python3
"""Advance the patch version after a prior release; leave the first at 1.0.0."""

import json
import re
import subprocess
from pathlib import Path


path = Path("package.json")
package = json.loads(path.read_text())
version = package["version"]
match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
if not match:
    raise ValueError(f"Invalid SemVer: {version}")
if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/v{version}"],
                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
    major, minor, patch = map(int, match.groups())
    version = f"{major}.{minor}.{patch + 1}"
    package["version"] = version
    path.write_text(json.dumps(package, indent=2) + "\n")
print(version)
