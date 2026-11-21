cask "contextlens-preview" do
  version "0.3.1-preview.2"
  sha256 "42373a29db99f592583d5dcaff1574ae6d75b34481b1fb8a3fa44e1217ea2a2d"

  url "https://github.com/bstack-tools/ContextLens/releases/download/v#{version}/ContextLens-#{version}-arm64.zip"
  name "ContextLens Preview"
  desc "Unnotarized preview of local window capture for coding agents"
  homepage "https://github.com/bstack-tools/ContextLens/"

  livecheck do
    skip "Preview releases are updated explicitly after verification"
  end

  conflicts_with cask: "contextlens"
  depends_on arch: :arm64
  depends_on macos: :sonoma
  container type: :zip

  app "ContextLens.app"
  binary "#{appdir}/ContextLens.app/Contents/MacOS/contextlens-cli"

  caveats <<~EOS
    Unnotarized preview: ad-hoc signed, without Developer ID or Apple verification.
    macOS may block the first launch. Verify the release origin and checksum first.
    If you trust this copy, try opening ContextLens, then use System Settings >
    Privacy & Security > Open Anyway and confirm Open. See:
      https://support.apple.com/en-us/102445
    Your Mac's policy may prevent authorization. CLI authorization may be separate.
    Keep macOS security enabled. Do not force an existing ContextLens replacement.
    Back up an existing app deliberately before switching channels; quit it first.
    Uninstall preserves ContextLens sessions, settings and exported packages.
  EOS
end
