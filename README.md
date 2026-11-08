# Brendan-Lim Homebrew tap

ContextLens distribution is pending Developer ID signing and Apple notarization. This repository currently contains a cask template and validation tooling. **There is no installable `contextlens` cask yet.**

Source: [Brendan-Lim/ContextLens](https://github.com/Brendan-Lim/ContextLens). The native app captures and annotates a selected macOS window and exports local visual context for coding agents.

Validate the pending template with `python3 scripts/validate.py`. It uses Ruby's parser without inventing a checksum or download. The workflow audits a real cask only after a verified release exists.

After publishing a signed, notarized release, use the source repository's `scripts/update-homebrew.py VERSION /path/to/this/tap` to download its actual assets, verify checksums/signatures/stapling/Gatekeeper, and generate `Casks/contextlens.rb`. Set `CONTEXTLENS_TEAM_ID` to the expected Apple signing team first. Review, audit and commit the result; the updater does not push or use cross-repository tokens.

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
