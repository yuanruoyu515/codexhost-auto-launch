# Changelog

## 1.0.0 — 2026-11-07

- Package the macOS cold-start helper from [codex-host#702](https://github.com/BytePioneer-AI/codex-host/pull/702) as an independent companion.
- Add per-user installation, readiness and live-injection checks, update instructions and uninstall commands.
- Migrate recognized older helper services while preserving their active supervisors and Desktop sessions.
- Recover a stuck supervisor owned by the listener, including its identified Desktop Controller children, when the next cold start has no other Desktop instance to protect.
- Add management tests, isolated macOS lifecycle tests, bilingual setup documentation and a [Tabs companion guide](https://github.com/yuanruoyu515/chatgpt-codex-tabs).
