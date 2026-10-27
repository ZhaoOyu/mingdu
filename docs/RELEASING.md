# Publishing a preview

The `Test and build` workflow builds Ubuntu deb, Linux Qt tar.gz, Windows portable ZIP and per-user Inno Setup installer, plus separate macOS arm64/Intel DMGs. The Windows runner needs Inno Setup 6; macOS uses system hdiutil. Build scripts must run on their target OS.

1. Update `brightness.__version__`, changelog, README download links, `docs/INSTALL.md` and `docs/RELEASE_NOTES.md`. Preview tags use `v<app version>-preview.<number>`; the installed application and asset filenames use the base app version. Example: app `1.1.0`, tag `v1.1.0-preview.1`.
2. Run lint and tests, commit and push to main. Tag that reviewed commit and push the tag:

   ```sh
   git tag v1.1.0-preview.1
   git push origin v1.1.0-preview.1
   ```

3. All four desktop jobs and the GTK job must succeed. Windows tests installation, installed-app single-instance startup, and uninstallation; macOS verifies DMG integrity. The release job downloads only artifacts from its own workflow run and rejects missing, duplicate or empty required packages.
4. The workflow creates a draft prerelease, uploads six packages plus installation instructions and SHA-256 checksums, then publishes it as a prerelease without marking it latest. Review the public release page and asset list.

A failed upload leaves a draft; rerun failed jobs to resume it. An already published release is never overwritten by this workflow. If a published package needs correction, publish a new preview tag, update links and release notes, and do not move the old tag. Tag publication requires all jobs from that tag to pass even if the main build already passed.

The workflow uses GitHub's scoped token (`contents: write`, `actions: read` only for the release job). No external release action or signing secret is required. Signing/notarization is not configured; document that limitation until credentials and verification steps are added. Do not describe these previews as stable or hardware-certified.

Installer references: [Inno Setup per-user installation](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm), [Apple distribution packaging](https://developer.apple.com/documentation/xcode/packaging-mac-software-for-distribution).
