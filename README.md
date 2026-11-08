# Brendan-Lim Homebrew tap

## Publication security

Both repositories' reachable histories and the existing preview were reviewed in the [public beta-readiness audit](https://github.com/Brendan-Lim/ContextLens/blob/main/docs/public-beta-readiness.md). Current recommendation: **controlled testers**; interactive first-run, fresh Screen Recording and capture/Hand Off acceptance remain pending.

Before committing cask/workflow changes, run `python3 scripts/audit-public-files.py --staged`, then the tracked-file audit without that flag. Use `--history` in a full clone for all reachable refs, `python3 scripts/run-gitleaks.py` for a pinned local independent scan, and `python3 scripts/check-public-links.py` for public Markdown links. `python3 -m unittest discover -s scripts/tests -v` tests these guards. The separate read-only Publication Security workflow runs the same checks; it does not upload source or raw scanner reports. See [safe output, optional local hook and incident response](https://github.com/Brendan-Lim/ContextLens/blob/main/docs/publication-security.md). Genuine sensitive history requires a separately approved remediation plan; never automatically force-push or replace release assets.

## Unnotarized preview channel

The separate `contextlens-preview` channel installs [ContextLens 0.3.0-preview.1](https://github.com/Brendan-Lim/ContextLens/releases/tag/v0.3.0-preview.1). The cask uses the verified published archive and actual SHA-256. [Candidate verification 42471268060](https://github.com/Brendan-Lim/homebrew-tap/actions/runs/42471268060) passed on a disposable arm64 macOS 15.8.2 runner with Homebrew 7.0.12: style, online audit, fetch/checksum, installation, app placement, CLI linking/help, quarantine retention, existing-app protection and uninstall preservation of session/export markers.

```sh
brew install --cask Brendan-Lim/tap/contextlens-preview
```

Try opening ContextLens from Applications, follow the authorization guidance below, and grant Screen Recording when requested. Then try `contextlens-cli --help`. Manual first-launch authorization, fresh-user permissions and interactive capture/Hand Off remain **pending**; the hosted runner's read-only Gatekeeper assessment correctly rejected the app. No Gatekeeper acceptance is claimed. macOS 14 runtime and upgrades from another preview remain untested.

The public GitHub browser download URL returned HTTP 504 during testing. The cask uses GitHub's official public asset API with `Accept: application/octet-stream`; this requires no GitHub account/token and serves the same verified ZIP. Homebrew's version includes both preview version and immutable asset ID (`0.3.0-preview.1,723563642`).

Previews are optimized arm64 builds for macOS 14+, ad-hoc signed without Developer ID signing or Apple notarization. Apple has not verified them. macOS can block first launch, and an installed CLI can require separate authorization. Only after verifying the official release origin and SHA-256, follow [Apple's Open Anyway instructions](https://support.apple.com/en-us/102445) if you choose to authorize the app. Keep macOS security and quarantine enabled. Managed Mac policies may prevent authorization.

The cask installs `ContextLens.app` and links its embedded `contextlens-cli`. It conflicts with the future stable cask and default Homebrew installation refuses to overwrite an existing app. Quit and deliberately back up an existing copy before switching channels; do not use force/adopt options. Both channels share the bundle ID, sessions and CLI name, so do not treat another app directory as isolation.

Preview uninstall preserves sessions, settings and exported packages: there is no `zap` or deletion hook. Hosted checks use only a disposable GitHub macOS runner; manual Gatekeeper authorization, fresh-user Screen Recording and interactive capture/Hand Off remain pending. [Full preview instructions and report](https://github.com/Brendan-Lim/ContextLens/blob/main/docs/preview-releases.md).

Maintainers: `python3 scripts/validate.py` checks both channel templates and generated casks. Generate a preview cask with the main repository's `python3 scripts/preview-release.py update-tap VERSION /path/to/tap`. Push candidates under `preview/**` to run style, online audit, fetch and disposable install/uninstall checks before promoting to main. `scripts/test-preview-install.py` refuses to run outside a GitHub-hosted runner and does not authorize or launch the GUI app.

## Official stable channel preparation

Official stable distribution is pending exact-candidate isolated interactive acceptance. This tap has separate pending templates for unnotarized official releases and future Developer ID/notarized releases. **There is no installable stable `contextlens` cask yet.** Project stability is not Apple verification.

Source: [Brendan-Lim/ContextLens](https://github.com/Brendan-Lim/ContextLens). The native app captures and annotates a selected macOS window and exports local visual context for coding agents.

Validate the pending template with `python3 scripts/validate.py`. It uses Ruby's parser without inventing a checksum or download. The workflow audits a real cask only after a verified release exists.

For the official ad-hoc channel, first complete the source repository's [release acceptance procedure](https://github.com/Brendan-Lim/ContextLens/blob/main/docs/release-acceptance/README.md). After its official release is published, use `scripts/update-homebrew.py VERSION /path/to/this/tap --unnotarized-official` from a clean source checkout with the pinned DMG build dependencies available. It downloads both containers, verifies signatures and matching bundles, checks exact acceptance and source-tag provenance, and renders the actual ZIP asset ID/checksum. The template discloses unnotarized signing, retains quarantine and conflicts with the preview. It never creates an installable cask pointing to an unpublished candidate. Review and independently push the generated cask, then verify clean installation before announcing availability.

Preview users must quit, save and back up sessions before switching. Once stable exists, uninstall only `contextlens-preview` (without `--zap`) before installing `Brendan-Lim/tap/contextlens`. Sessions and exports remain; never force/adopt an existing app. Reopen the saved session and verify annotations before removing backups. See [full migration instructions](https://github.com/Brendan-Lim/ContextLens/blob/main/docs/homebrew.md).

For the unchanged Developer ID path, after publishing a signed, notarized release, use the source repository's `scripts/update-homebrew.py VERSION /path/to/this/tap` to download its actual assets, verify checksums/signatures/stapling/Gatekeeper, and generate `Casks/contextlens.rb`. Set `CONTEXTLENS_TEAM_ID` to the expected Apple signing team first. Review, audit and commit the result; the updater does not push or use cross-repository tokens.

After that cask is published and installation tested, the intended commands are:

```sh
brew install --cask Brendan-Lim/tap/contextlens
open -a ContextLens
contextlens-cli --help
brew update
brew upgrade --cask contextlens
brew uninstall --cask contextlens
```

These commands are pending release verification. Uninstall will remove the app and CLI link; no `zap` stanza deletes sessions or exported evidence. Move an existing manually installed app to a safe backup location before a future real installation; do not use `--force` to overwrite it.
