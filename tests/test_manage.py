"""Manager contract tests. No LaunchAgent or production app is changed."""
import importlib.util
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("manage", ROOT / "manage.py")
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


class ManagerTests(unittest.TestCase):
    def test_plist_preserves_spaces_and_active_supervisors(self):
        home = Path("/Users/test user")
        launcher = Path("/Applications/my host/codexhost")
        config = plistlib.loads(plistlib.dumps(manage.agent_configuration(home, launcher)))
        self.assertEqual(config["ProgramArguments"][2], str(launcher))
        self.assertEqual(config["ProgramArguments"][0], str(manage.paths(home)[0] / "codexhost-auto-launch"))
        self.assertTrue(config["AbandonProcessGroup"])
        self.assertEqual(config["EnvironmentVariables"]["CODEXHOST_CONSOLE"], "0")
        self.assertTrue(config["KeepAlive"])
        self.assertEqual(config["Umask"], 0o077)

    def test_symlinks_and_directories_are_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "user-file"
            target.write_text("keep")
            link = root / "symlink"
            link.symlink_to(target)
            for path in (root, link):
                with self.assertRaises(ValueError):
                    manage.require_regular_file_or_missing(path)
            manage.require_regular_file_or_missing(target)
            manage.require_regular_file_or_missing(root / "absent")
            self.assertEqual(target.read_text(), "keep")

    def test_launcher_wrappers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "launcher"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
            with self.assertRaises(ValueError):
                manage.validate_launcher(executable)
            executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"test")
            self.assertEqual(manage.validate_launcher(executable), executable.resolve())

    def test_legacy_migration_keeps_runtime_and_backs_up_plist(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            support, _ = manage.paths(home)
            old_label, old_relative = manage.LEGACY[0]
            plist = home / "Library/LaunchAgents" / (old_label + ".plist")
            plist.parent.mkdir(parents=True)
            content = plistlib.dumps({"Label": old_label, "AbandonProcessGroup": True,
                "ProgramArguments": [str(home / "Library/Application Support" / old_relative)]})
            plist.write_bytes(content)
            calls = []
            def fake_launchctl(*args, **kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0, "", "")
            with mock.patch.object(manage, "launchctl", side_effect=fake_launchctl):
                manage.migrate_legacy(home, support)
            self.assertFalse(plist.exists())
            backup = list((support / "backups").glob("*/*.plist"))
            self.assertEqual(len(backup), 1)
            self.assertEqual(backup[0].read_bytes(), content)
            self.assertTrue(any(call[0] == "bootout" for call in calls))
            self.assertFalse(any(call[0] in ("kill", "stop") for call in calls))

    def test_unrecognized_legacy_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            label, _ = manage.LEGACY[0]
            plist = home / "Library/LaunchAgents" / (label + ".plist")
            plist.parent.mkdir(parents=True)
            content = plistlib.dumps({"Label": label, "ProgramArguments": ["/unrelated/program"]})
            plist.write_bytes(content)
            with self.assertRaises(ValueError):
                manage.legacy_agents(home)
            self.assertEqual(plist.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
