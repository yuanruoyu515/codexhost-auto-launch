#!/usr/bin/env python3
"""Install, inspect, or remove CodexHost Auto Launch for the current user."""

import argparse
import datetime
import json
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

LABEL = "com.ruoyu.codexhost.auto-launch"
ROOT = Path(__file__).resolve().parent
LEGACY = (
    ("com.ruoyu.codexhost.autoinject", "codexhost-autoinject/codexhost-autoinject"),
    ("ai.bytepioneer.codexhost.auto-launch", "codexhost/auto-launch/codexhost-auto-launch"),
)


def paths(home):
    support = home / "Library/Application Support/codexhost-auto-launch"
    plist = home / "Library/LaunchAgents" / (LABEL + ".plist")
    return support, plist


def agent_configuration(home, launcher):
    support, _ = paths(home)
    return {
        "Label": LABEL,
        "ProgramArguments": [
            str(support / "codexhost-auto-launch"),
            "--launcher",
            str(launcher),
            "--data-directory",
            str(support),
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 30,
        "LimitLoadToSessionType": "Aqua",
        "ProcessType": "Background",
        # Removing/updating the listener must not kill its active supervisor.
        "AbandonProcessGroup": True,
        "Umask": 0o077,
        "EnvironmentVariables": {
            "CODEXHOST_CONSOLE": "0",
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        },
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": str(support / "service.log"),
    }


def launchctl(*arguments, check=True):
    return subprocess.run(
        ["/bin/launchctl", *arguments], check=check, capture_output=True, text=True, timeout=15
    )


def require_regular_file_or_missing(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Refusing to replace a non-regular file: " + str(path))


def validate_launcher(launcher):
    if not launcher.is_absolute():
        raise ValueError("--launcher must be an absolute path")
    launcher = launcher.resolve(strict=True)
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise ValueError("The CodexHost launcher must be executable")
    # Native executables retain the process identity used by the listener.
    with launcher.open("rb") as stream:
        magic = stream.read(4)
    if magic not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf",
                     b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
                     b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca"):
        raise ValueError("Choose a native CodexHost executable, not an npm or shell wrapper")
    return launcher


def legacy_agents(home):
    found = []
    for label, relative in LEGACY:
        plist = home / "Library/LaunchAgents" / (label + ".plist")
        if not plist.exists() and not plist.is_symlink():
            continue
        require_regular_file_or_missing(plist)
        configuration = plistlib.loads(plist.read_bytes())
        expected = str(home / "Library/Application Support" / relative)
        args = configuration.get("ProgramArguments", [])
        if (configuration.get("Label") != label or not args or args[0] != expected
                or configuration.get("AbandonProcessGroup") is not True):
            raise ValueError("Legacy helper needs manual review before migration: " + str(plist))
        found.append((label, plist))
    return found


def migrate_legacy(home, support):
    found = legacy_agents(home)
    if not found:
        return
    backup = support / "backups" / datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True)
    for label, plist in found:
        shutil.copy2(plist, backup / plist.name)
        target = "gui/{}/{}".format(os.getuid(), label)
        if launchctl("print", target, check=False).returncode == 0:
            launchctl("bootout", target)
        plist.unlink()
        print("Migrated legacy listener: " + label)


def install(home, launcher, target):
    launcher = validate_launcher(launcher)
    legacy_agents(home)
    support, plist = paths(home)
    source = Path(__file__).resolve().parent
    support.mkdir(parents=True, exist_ok=True)
    support.chmod(0o700)
    (support / "src").mkdir(exist_ok=True)
    plist.parent.mkdir(parents=True, exist_ok=True)
    binary = support / "codexhost-auto-launch"
    temporary = support / "codexhost-auto-launch.new"
    copied = ("src/AutoLaunch.swift", "manage.py", "install.py", "uninstall.py", "doctor.py", "VERSION")
    for path in (binary, temporary, plist, plist.with_suffix(".plist.new"),
                 support / "install.json", *(support / name for name in copied)):
        require_regular_file_or_missing(path)
    for name in copied:
        if not (source / name).is_file():
            raise ValueError("Source file is missing: " + name)
    machine = platform.machine()
    if machine not in ("arm64", "x86_64"):
        raise ValueError("Unsupported macOS architecture: " + machine)
    subprocess.run(
        [
            "/usr/bin/xcrun", "swiftc", "-swift-version", "6", "-parse-as-library",
            "-O", "-target", machine + "-apple-macosx13.0",
            str(source / "src/AutoLaunch.swift"), "-o", str(temporary),
        ],
        check=True,
    )
    subprocess.run(
        ["/usr/bin/codesign", "--force", "--sign", "-", str(temporary)], check=True
    )
    if launchctl("print", target, check=False).returncode == 0:
        launchctl("bootout", target)
    os.replace(temporary, binary)
    for name in copied:
        origin, destination = source / name, support / name
        require_regular_file_or_missing(destination)
        if origin.resolve() != destination.resolve():
            shutil.copy2(origin, destination)
    plist_temporary = plist.with_suffix(".plist.new")
    require_regular_file_or_missing(plist_temporary)
    plist_temporary.write_bytes(plistlib.dumps(agent_configuration(home, launcher)))
    plist_temporary.chmod(0o600)
    os.replace(plist_temporary, plist)
    (support / "install.json").write_text(json.dumps({
        "version": (source / "VERSION").read_text().strip(),
        "launcher": str(launcher),
        "installedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }, indent=2) + "\n")
    migrate_legacy(home, support)
    launchctl("enable", target)
    launchctl("bootstrap", target.rsplit("/", 1)[0], str(plist))
    launchctl("kickstart", target)
    for _ in range(40):
        observed = launchctl("print", target, check=False)
        if any(line.strip() == "state = running" for line in observed.stdout.splitlines()):
            break
        time.sleep(0.1)
    else:
        raise RuntimeError("Listener did not start. Check service.log and run python3 doctor.py")
    print("Installed: " + target)
    print("Existing Desktop sessions remain open; the next cold start is observed.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "status", "uninstall"))
    parser.add_argument(
        "--launcher", type=Path,
        default=Path("/Applications/codexhost.app/Contents/MacOS/codexhost"),
        help="Absolute native codexhost executable path (install only)",
    )
    arguments = parser.parse_args(argv)
    if platform.system() != "Darwin":
        parser.error("This automation is available only on macOS")
    if os.getuid() == 0:
        parser.error("Run as the logged-in user, without sudo")
    if not arguments.launcher.is_absolute():
        parser.error("--launcher must be an absolute executable path")
    home = Path.home()
    support, plist = paths(home)
    target = "gui/{}/{}".format(os.getuid(), LABEL)
    if arguments.command == "install":
        install(home, arguments.launcher, target)
    elif arguments.command == "status":
        observed = launchctl("print", target, check=False)
        state = next(
            (line.strip() for line in observed.stdout.splitlines()
             if line.strip().startswith("state = ")),
            "state = not-loaded",
        )
        print(state)
        print("plist = " + str(plist))
        print("logs = " + str(support))
        return 0 if state == "state = running" else 1
    else:
        if launchctl("print", target, check=False).returncode == 0:
            launchctl("bootout", target)
        require_regular_file_or_missing(plist)
        if plist.exists():
            plist.unlink()
        print("Uninstalled. Existing Desktop sessions remain open.")
        print("Source and logs retained at: " + str(support))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
