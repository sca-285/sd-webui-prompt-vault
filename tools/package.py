"""The release zip: python3 tools/package.py -> dist/sd-webui-prompt-vault-<version>.zip

What the WebUI needs, in a folder of the extension's name (unzip it into extensions/);
no tests, no tools, no CI. Built from the last commit, so commit first."""
import os, re, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "sd-webui-prompt-vault"
LEAVE_OUT = ("tests", "tools", ".github", ".gitignore")

version = re.search(r'VERSION = "([^"]+)"', open(os.path.join(REPO, "lib_vault", "__init__.py")).read()).group(1)
os.makedirs(os.path.join(REPO, "dist"), exist_ok=True)
out = os.path.join(REPO, "dist", f"{NAME}-{version}.zip")
paths = [p for p in subprocess.run(["git", "ls-tree", "--name-only", "HEAD"], cwd=REPO, capture_output=True, text=True,
                                   check=True).stdout.split() if p not in LEAVE_OUT]
subprocess.run(["git", "archive", "--format=zip", f"--prefix={NAME}/", "-o", out, "HEAD", "--", *paths], cwd=REPO, check=True)
print(f"{out} ({os.path.getsize(out) / 1e6:.1f} MB)")
sys.exit(0)
