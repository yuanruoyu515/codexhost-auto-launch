#!/usr/bin/env python3
"""Read-only checks for listener readiness; --live also requires working injection."""

import argparse
import json
import os
import platform
import plistlib
import subprocess
from pathlib import Path

import manage


def live_pid(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Require current CodexHost injection too")
    args = parser.parse_args(argv)
    if platform.system() != "Darwin":
        print("[!!] macOS is required")
        return 1
    home = Path.home()
    support, plist = manage.paths(home)
    target = "gui/{}/{}".format(os.getuid(), manage.LABEL)
    healthy = True

    def check(ok, label, detail=""):
        nonlocal healthy
        print("[{}] {}{}".format("ok" if ok else "!!", label, ": " + detail if detail else ""))
        healthy = healthy and ok

    check(True, "macOS", platform.mac_ver()[0])
    configuration = {}
    try:
        configuration = plistlib.loads(plist.read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException):
        pass
    check(bool(configuration), "Listener installed", "Run python3 install.py" if not configuration else manage.LABEL)
    observed = manage.launchctl("print", target, check=False)
    running = any(line.strip() == "state = running" for line in observed.stdout.splitlines())
    check(running, "Listener running", "Run python3 install.py again" if not running else "listening for future launches")
    program = configuration.get("ProgramArguments", [])
    launcher = Path(program[program.index("--launcher") + 1]) if "--launcher" in program and program.index("--launcher") + 1 < len(program) else Path("/Applications/codexhost.app/Contents/MacOS/codexhost")
    executable = launcher.is_file() and os.access(launcher, os.X_OK)
    check(executable, "CodexHost executable", str(launcher))
    for label, _ in manage.LEGACY:
        old = manage.launchctl("print", "gui/{}/{}".format(os.getuid(), label), check=False)
        if old.returncode == 0:
            check(False, "Duplicate legacy listener", label + "; run python3 install.py to migrate")
    metadata = read_json(support / "install.json")
    if metadata:
        print("[info] Helper version: " + str(metadata.get("version", "unknown")))

    inspection = {}
    if executable:
        try:
            result = subprocess.run([str(launcher), "inspect", "--json"], capture_output=True, text=True, timeout=8)
            inspection = json.loads(result.stdout) if result.returncode == 0 else {}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    runtime = inspection.get("runtime", {})
    desktop = inspection.get("desktop") or {}
    attached = runtime.get("running") is True
    controller = read_json(home / ".codexhost/diagnostics/desktop-controller-v1.json")
    renderer = controller.get("renderer", {})
    injected = attached and live_pid(controller.get("pid")) and renderer.get("state") == "installed"
    if injected:
        print("[ok] Current injection: installed; CodexHost " + str(inspection.get("launcherVersion", "unknown")))
    elif args.live:
        check(False, "Current injection", "Quit Desktop when convenient, then open it normally. Read events.jsonl if it still fails")
    elif desktop.get("processIds"):
        print("[info] Desktop is open without verified injection. The listener only handles future cold starts")
    else:
        print("[info] No verified live injection. Desktop can stay closed; readiness does not require opening it")
    check(bool(desktop) or any((Path("/Applications") / name / "Contents/Resources/app.asar").is_file()
                             for name in ("ChatGPT.app", "Codex.app")),
          "Electron Desktop installation", "ChatGPT / Codex with the com.openai.codex bundle ID")
    print("[info] Tabs companion: https://github.com/yuanruoyu515/chatgpt-codex-tabs")
    print("[info] Local logs: " + str(support))
    return 0 if healthy else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print("[!!] Diagnostic failed: " + str(error))
        raise SystemExit(1)
