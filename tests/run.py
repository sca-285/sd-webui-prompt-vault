"""Every check of the extension, each in a WebUI data folder of its own.

    python3 tests/run.py            all of them (the chip coverage takes a few minutes)
    python3 tests/run.py --quick    without the chip coverage, and 800 ideas instead of 4000

Needs fastapi, httpx, pillow and requests (the WebUI has them); the WebUI itself is stubbed in tests/stub."""
import glob, hashlib, os, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PY = sys.executable
CHECKS = [
    ("tags, never prose", ["tools/muse_scenes/lint.py"]),
    ("scenes match their sources", None),
    ("api, lock and roll", ["tests/test_api.py"]),
    ("group sizes", ["tests/test_groups.py"]),
    ("random ideas: adults, bodies, skies, jobs", ["tests/check_ideas.py"]),
    ("every act for every cast", ["tests/check_acts.py"]),
    ("every kink: 25 scenes or more", ["tests/check_kinks.py"]),
    ("every chip: 25 scenes or more", ["tests/check_chips.py"]),
    ("every part: ten values or more to roll", ["tests/check_variety.py"]),
    ("qwen chat, memory placement", ["tests/test_chat.py"]),
    ("javascript parses", "js"),
]


def _hashes():
    folder = os.path.join(REPO, "data", "muse_scenes")
    return {f: hashlib.sha1(open(os.path.join(folder, f), "rb").read()).hexdigest() for f in sorted(os.listdir(folder))}


def rebuilt():
    """The data/muse_scenes files are what tools/muse_scenes writes, byte for byte."""
    before = _hashes()
    out = subprocess.run([PY, "tools/muse_scenes/build.py"], cwd=REPO, capture_output=True, text=True)
    if out.returncode:
        return out.returncode, out.stdout + out.stderr
    after = _hashes()
    changed = sorted(f for f in set(before) | set(after) if before.get(f) != after.get(f))
    return (1 if changed else 0), ("rewritten: " + ", ".join(changed)) if changed else "the same"


def main():
    quick = "--quick" in sys.argv
    failed = []
    for name, cmd in CHECKS:
        if quick and isinstance(cmd, list) and cmd[0].endswith("check_chips.py"):
            continue
        start = time.time()
        if cmd is None:
            code, text = rebuilt()
        elif cmd == "js":
            node = shutil.which("node")
            if not node:
                print("skip javascript parses (no node)")
                continue
            outs = [subprocess.run([node, "--check", f], cwd=REPO, capture_output=True, text=True)
                    for f in sorted(glob.glob(os.path.join(REPO, "javascript", "*.js")))]
            code, text = max(o.returncode for o in outs), "".join(o.stderr for o in outs)
        else:
            data = tempfile.mkdtemp(prefix="pv-test-")
            env = dict(os.environ, STUB=os.path.join(HERE, "stub"), PV_TEST_DATA=data, PYTHONDONTWRITEBYTECODE="1")
            if quick:
                env["N"] = "800"
            out = subprocess.run([PY] + cmd, cwd=REPO, env=env, capture_output=True, text=True)
            shutil.rmtree(data, ignore_errors=True)
            code, text = out.returncode, out.stdout + out.stderr
        print(f"{'ok  ' if code == 0 else 'FAIL'} {name} ({time.time() - start:.0f}s)")
        if code:
            failed.append(name)
            print("\n".join("     " + line for line in text.strip().splitlines()[-25:]))
    print("all passed" if not failed else f"{len(failed)} failed: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
