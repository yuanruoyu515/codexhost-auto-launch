# Reporting a security issue

Do not include credentials, access tokens, conversation content or complete local logs in a public issue. For a security report, use [GitHub's private vulnerability reporting](https://github.com/yuanruoyu515/codexhost-auto-launch/security/advisories/new) if available.

The listener runs as your user and calls your installed CodexHost launcher. It does not contact a server or read account credentials. CodexHost's debug port gives local programs control of Desktop; do not expose that port to the network.

Only install source and binaries you trust. The default installation compiles the helper on your Mac. The helper is independently maintained and is not an official release of OpenAI or CodexHost.
