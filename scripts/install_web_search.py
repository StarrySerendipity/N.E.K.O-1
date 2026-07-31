"""Standalone .neko-plugin installer — uses only Python stdlib."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
import tomllib

PACKAGE = Path(r"D:\N.E.K.O\N.E.K.O自强之路\2026.06.10\N.E.K.O-1\plugin\neko_plugin_cli\target\web_searching.neko-plugin")
PLUGINS_ROOT = Path(r"C:\Users\Yanfq\AppData\Local\N.E.K.O\plugins")
PROFILES_ROOT = Path(r"C:\Users\Yanfq\AppData\Local\N.E.K.O\.neko-package-profiles")

def install():
    print(f"Installing: {PACKAGE.name}")
    print(f"  -> plugins_root: {PLUGINS_ROOT}")
    print(f"  -> profiles_root: {PROFILES_ROOT}")

    PLUGINS_ROOT.mkdir(parents=True, exist_ok=True)
    PROFILES_ROOT.mkdir(parents=True, exist_ok=True)

    # Extract to temp
    tmpdir = Path(tempfile.mkdtemp(prefix="neko_install_"))
    try:
        with zipfile.ZipFile(PACKAGE, "r") as zf:
            zf.extractall(tmpdir)

        # Read manifest
        manifest_path = tmpdir / "manifest.toml"
        manifest = tomllib.load(open(manifest_path, "rb"))
        plugin_id = manifest.get("id", "web_search")
        package_name = manifest.get("package_name", plugin_id)
        version = manifest.get("version", "0.1.0")
        print(f"  plugin_id: {plugin_id}")
        print(f"  package_name: {package_name}")
        print(f"  version: {version}")

        # Copy plugin files
        src_plugin = tmpdir / "payload" / "plugins" / plugin_id
        dst_plugin = PLUGINS_ROOT / plugin_id

        if dst_plugin.exists():
            shutil.rmtree(dst_plugin)
        shutil.copytree(src_plugin, dst_plugin)
        print(f"  Installed to: {dst_plugin}")

        # Copy profile
        src_profile = tmpdir / "payload" / "profiles" / f"{plugin_id}.toml"
        if src_profile.exists():
            dst_profile_dir = PROFILES_ROOT / plugin_id
            if dst_profile_dir.exists():
                shutil.rmtree(dst_profile_dir)
            dst_profile_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_profile, dst_profile_dir / f"{plugin_id}.toml")
            print(f"  Profile to: {dst_profile_dir}")

        # Verify entry in installed plugin.toml
        installed_toml = tomllib.load(open(dst_plugin / "plugin.toml", "rb"))
        entry = installed_toml.get("plugin", {}).get("entry", "")
        print(f"  Installed entry: {entry}")
        if entry.startswith(f"plugins.{plugin_id}:"):
            print("  [OK] Entry is user-mode (plugins.<id>:Class)")
        else:
            print(f"  [WARN] Entry does not match expected pattern: plugins.{plugin_id}:")

        # List installed files
        print("\n  Installed files:")
        for p in sorted(dst_plugin.rglob("*")):
            if p.is_file():
                print(f"    {p.relative_to(dst_plugin)}")

        return True

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    ok = install()
    sys.exit(0 if ok else 1)
