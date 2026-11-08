# Contributing

Start with the smallest reproducible launch sequence: which app was open, how it was opened, whether CodexHost was already running, and which component failed. Include macOS, Desktop and CodexHost versions. Review logs for sensitive output before sharing them.

## Run the checks

Python management tests run on macOS or Linux:

```bash
python3 -m unittest discover -s tests -p 'test_manage.py' -v
```

The lifecycle test needs macOS, Swift 6 and a desktop session:

```bash
python3 tests/test_lifecycle.py
```

It creates a unique fixture app in a temporary directory and never registers the production LaunchAgent. It exercises macOS notifications, launch handoffs and recovery. A passing fixture is not proof that every CodexHost/Desktop version can inject successfully; report real-app checks separately, and obtain authorization before interrupting someone else's active session.

## Keep these behaviors

- Listener installation and removal preserve active Desktop sessions.
- No changes to official app bundles, signatures, Dock items or global launch environments.
- Missing executables and failed launches do not create restart loops.
- Stale recovery is restricted to the listener's own supervisor and identified Controller children, with other Desktop instances protected.
- Custom executable paths and home directories containing spaces remain separate process arguments.
- No account credentials or conversation content are collected.

Keep the English and Chinese READMEs in sync when changing setup or behavior. Update `CHANGELOG.md` for user-visible changes. `VERSION` is the helper's version, independent of CodexHost.

The repository is MIT licensed. Contributions are accepted under that license. The original upstream proposal is [codex-host#702](https://github.com/BytePioneer-AI/codex-host/pull/702); this project can be used without that PR being merged.
