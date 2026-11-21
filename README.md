# Brendan-Lim Homebrew tap

Homebrew casks for **[ContextLens](https://github.com/bstack-tools/ContextLens)**, a native Mac app that captures and annotates a window you choose and hands the result to your coding agent.

## Install the preview

```sh
brew install --cask Brendan-Lim/tap/contextlens-preview
```

This installs [ContextLens 0.3.0-preview.1](https://github.com/bstack-tools/ContextLens/releases/tag/v0.3.0-preview.1) and links `contextlens-cli`. The cask uses the published release archive and its exact SHA-256, and is install-tested on a GitHub-hosted macOS runner.

**First launch.** Previews are Apple Silicon builds for macOS 14+ that aren't notarized by Apple yet, so macOS asks you to confirm the first time:

1. Open ContextLens from Applications and close the "can't verify" message.
2. Go to **System Settings → Privacy & Security** and click **Open Anyway** ([Apple's guide](https://support.apple.com/en-us/102445)).
3. Allow **Screen Recording** when prompted, then try `contextlens-cli --help`.

Keep macOS security and quarantine enabled, and only authorize a copy from the official release.

**Uninstall.** `brew uninstall --cask contextlens-preview` removes the app and CLI link. Your sessions, settings and exports are kept.

## Stable channel

There is no stable `contextlens` cask yet. It will be published after the first official release passes acceptance testing, and later as a Developer ID–signed, notarized build. When it arrives, uninstall `contextlens-preview` (without `--zap`) before installing `Brendan-Lim/tap/contextlens`. Both channels share the same bundle ID and sessions. See the [migration guide](https://github.com/bstack-tools/ContextLens/blob/main/docs/homebrew.md).

<details>
<summary><strong>For maintainers</strong></summary>

**Before committing** cask or workflow changes:

```sh
python3 scripts/audit-public-files.py --staged   # then again without --staged; add --history in a full clone
python3 scripts/run-gitleaks.py                  # pinned local secret scan
python3 scripts/check-public-links.py            # public Markdown links
python3 scripts/validate.py                      # channel templates and generated casks
python3 -m unittest discover -s scripts/tests -v
```

The read-only Publication Security workflow runs the same checks. See [publication security](https://github.com/bstack-tools/ContextLens/blob/main/docs/publication-security.md). Never force-push or replace release assets automatically.

**Preview casks** are generated from the main repository with `python3 scripts/preview-release.py update-tap VERSION /path/to/tap`. Push candidates to `preview/**` to run style, online audit, fetch and disposable install/uninstall checks before promoting to `main`. The cask downloads through GitHub's public asset API (`Accept: application/octet-stream`, no token needed) because the browser download URL returned HTTP 504 during testing.

**Stable casks** are generated with the main repository's `scripts/update-homebrew.py VERSION /path/to/this/tap`. Add `--unnotarized-official` for the ad-hoc channel after the [release acceptance procedure](https://github.com/bstack-tools/ContextLens/blob/main/docs/release-acceptance/README.md). For the notarized channel, set `CONTEXTLENS_TEAM_ID` first. The updater verifies checksums, signatures and provenance, and it never pushes or creates a cask for an unpublished release. Review, audit and push the result yourself, then verify a clean install before announcing it.

Full details: [preview releases](https://github.com/bstack-tools/ContextLens/blob/main/docs/preview-releases.md)

</details>
