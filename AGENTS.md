# Set up CodexHost Auto Launch

Human documentation: [README.md](README.md), [简体中文](README.zh-CN.md).

This is a macOS companion for CodexHost. It observes future cold starts and invokes the existing native `codexhost launch` command. It does not implement injection itself.

## Installation rules

- Keep the user's current Desktop session open. Installation and listener migration do not require restarting it.
- Explain that future cold starts restart once, and initial file-open/deep-link requests are not forwarded. Do not deliberately restart an active session unless the user already authorized that action.
- Do not patch, copy or re-sign either application in `/Applications`. The installer signs only its own newly compiled helper.
- Run as the logged-in user, without `sudo`. Do not install CodexHost or Xcode tools without the user's authorization.
- Use the native CodexHost executable. An npm entry point or shell wrapper does not provide the process identity this listener checks.
- Keep normal readiness and live injection distinct. A closed app is allowed for `doctor.py`; `doctor.py --live` requires working current injection.
- Never upload local logs or credentials as part of setup.

## 1. Check prerequisites

```bash
sw_vers -productVersion
python3 --version
xcrun swiftc --version
ls -d /Applications/ChatGPT.app /Applications/Codex.app 2>/dev/null
ls -l /Applications/codexhost.app/Contents/MacOS/codexhost
```

Requirements: macOS 13+, Swift 6, Python 3.9+, an Electron Desktop with bundle ID `com.openai.codex` and `app.asar`, and a working CodexHost installation. A separate native ChatGPT app is not supported.

If prerequisites are missing, identify the missing piece and link its official installation instructions. For CodexHost: https://github.com/BytePioneer-AI/codex-host. The helper does not install those dependencies.

## 2. Install

```bash
git clone https://github.com/yuanruoyu515/codexhost-auto-launch.git
cd codexhost-auto-launch
python3 install.py
```

For a custom native launcher:

```bash
python3 install.py --launcher /absolute/path/to/native/codexhost
```

The installer compiles locally, copies runtime and management files to `~/Library/Application Support/codexhost-auto-launch/`, and registers `com.ruoyu.codexhost.auto-launch`.

It migrates recognized predecessor helpers with the labels `com.ruoyu.codexhost.autoinject` and `ai.bytepioneer.codexhost.auto-launch`. Their plists are backed up; their logs and active supervisors are preserved. Do not manually kill CodexHost processes to complete a normal installation. If legacy configuration validation fails, inspect the reported plist instead of bypassing the check.

## 3. Verify

```bash
python3 doctor.py
```

Report the output and exit code. Exit 0 means readiness checks passed; it does not by itself mean a new cold start was tested.

If the app is already running under CodexHost:

```bash
python3 doctor.py --live
```

Do not quit an existing app just to make this check pass. Explain how the user can test a cold start when convenient. The helper ignores sessions that predate listener startup.

## 4. Optional Tabs companion

The related tab bar is https://github.com/yuanruoyu515/chatgpt-codex-tabs. It is a separate installation. When the user wants both, follow that repository's current AGENTS.md and use its CodexHost mode (`python3 install.py`, without `--standalone`). Do not install the extra project merely because it is linked here.

## 5. Uninstall

```bash
python3 uninstall.py
```

Without the checkout:

```bash
python3 "$HOME/Library/Application Support/codexhost-auto-launch/uninstall.py"
```

This removes the listener, preserving active Desktop sessions and local source/logs. Do not delete those retained files unless the user requests cleanup.

## Development

```bash
python3 -m unittest discover -s tests -p 'test_manage.py' -v
python3 tests/test_lifecycle.py
```

Lifecycle tests use a unique fixture app and temporary paths. They must never target the production `com.openai.codex` identity. Preserve the checks that protect existing sessions, reject duplicate listeners and limit recovery to a supervisor owned by this listener.
