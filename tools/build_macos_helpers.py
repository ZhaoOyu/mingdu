"""Build pinned upstream helpers; ship licenses and exact source with the app."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HELPERS = {
    "brightness": ("https://github.com/nriley/brightness.git", "bbbe5a26cf8fc0496801c1af84cee9ba53f27a51", "brightness", "BSD-2-Clause"),
    "m1ddc": ("https://github.com/waydabber/m1ddc.git", "7339ceebb03f691b1eaeb8471dca301d215d19c8", "m1ddc", "MIT"),
    "ddcctl": ("https://github.com/kfix/ddcctl.git", "06c7ab6eba5b1c903678f8113a92cef990acaf90", "bin/release/ddcctl", "GPL-3.0"),
}


def helper_names(machine=None):
    machine = machine or platform.machine().lower()
    if machine not in ("arm64", "aarch64", "x86_64", "amd64"):
        raise ValueError(f"Unsupported Mac architecture: {machine}")
    return ("brightness", "m1ddc" if machine in ("arm64", "aarch64") else "ddcctl")


def build_helpers():
    if sys.platform != "darwin":
        raise RuntimeError("Build macOS helpers on macOS with Xcode command-line tools")
    destination = ROOT / "build/macos-helpers"
    source_root = ROOT / "build/macos-helper-sources"
    # Never package stale binaries for a different architecture.
    if destination.exists():
        shutil.rmtree(destination)
    binaries, docs = destination / "bin", destination / "docs"
    binaries.mkdir(parents=True)
    docs.mkdir()
    environment = dict(os.environ)
    environment.setdefault("CLANG_MODULE_CACHE_PATH", str(ROOT / "build/clang-module-cache"))
    manifest = []
    for name in helper_names():
        url, commit, product, license_name = HELPERS[name]
        source = source_root / name
        if not (source / ".git").is_dir():
            source.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "init", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "remote", "add", "origin", url], check=True)
        current = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"],
                                 capture_output=True, text=True)
        if current.returncode or current.stdout.strip() != commit:
            subprocess.run(["git", "-C", str(source), "fetch", "--depth", "1", url, commit], check=True)
            subprocess.run(["git", "-C", str(source), "checkout", "--detach", commit], check=True)
        # Refuse locally modified source rather than mislabel its provenance.
        subprocess.run(["git", "-C", str(source), "diff", "--exit-code", "HEAD"], check=True)
        subprocess.run(["make", "clean"], cwd=source, env=environment, check=True)
        subprocess.run(["make"], cwd=source, env=environment, check=True)
        binary = binaries / name
        shutil.copy2(source / product, binary)
        binary.chmod(0o755)
        arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x86_64"
        subprocess.run(["lipo", str(binary), "-verify_arch", arch], check=True)
        shutil.copy2(source / "LICENSE", docs / f"{name}-LICENSE.txt")
        archive = docs / f"{name}-source.tar.gz"
        subprocess.run(["git", "-C", str(source), "archive", "--format=tar.gz",
                        f"--prefix={name}/", "--output", str(archive), commit], check=True)
        manifest.append({"name": name, "repository": url, "commit": commit, "license": license_name,
                         "source_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
    (docs / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (docs / "README.txt").write_text(
        "These unmodified tools run as separate subprocesses. Each retains its own license.\n"
        "The exact corresponding source, Makefiles and license notices are included beside this file.\n"
        "To rebuild on the matching Mac architecture, extract the source archive and run make\n"
        "with Apple Xcode command-line tools installed. No extra libraries are required.\n"
        "Only brightness and the DDC helper for this architecture are bundled.\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    print(build_helpers())
