# Security

Engineering Workshop is a **trusted local Python and JavaScript runner** for one person. Exercise code runs with that person's filesystem and network permissions. Time/output limits and a temporary directory do not make it a sandbox. Do not expose the server publicly, run it as an administrator, or execute code you do not trust.

The server binds to loopback, validates Host and Origin, and rejects cross-site requests. No account or API key is needed. Framework packages are installed during setup; exercise code and learner state stay local unless you explicitly share them.

## Session token

Every API request must send the session token, except `/api/health` and the files of imported books. This covers reading and changing progress, drafts, notes, project state, reading state, game state and backups, and running exercise code.

- The server keeps the token in the `session-token` file in the data folder. The token stays the same when the server restarts. The server makes a new one only when the file is missing.
- The launcher, the app shortcuts, the installers and the native Mac window open `http://127.0.0.1:7318/#session=<token>`. The browser does not send the part after `#` to the server. The page saves the token in the browser's local storage and removes it from the address bar.
- No endpoint returns the token. A browser without it shows "Open Engineering Workshop from its shortcut or start command to connect this browser".
- The app's page files, `/api/health` and book files (covers, images, the original PDF or EPUB) do not need the token. The browser loads book files by URL, so it cannot send the token with them.
- Another program that runs as your user account can read the token file. The token protects against other accounts on the computer and against web pages, not against software you run yourself.

## File permissions

On macOS and Linux, the server and the install command create the data folder as `0700` and its files as `0600`, so other accounts on the computer cannot read your progress, notes, backups or the token. They also set the data folder of an older install to `0700`. On Windows, the install folder is in `%LOCALAPPDATA%`, which other standard accounts cannot read. In a Windows clone, the `data` folder has the same permissions as the clone folder.

## Verify a download

The install commands check every download before they use it:

- The app archive must match the `SHA256SUMS` file published with the same release.
- uv and Node.js must match SHA-256 hashes written into `install.sh` and `install.ps1`.
- Python packages come from `requirements.lock` or `requirements-light.lock`, which list a SHA-256 hash for every file. Setup installs them with `--require-hashes`.

Releases made by the current release workflow also carry a GitHub build provenance attestation. It shows that this repository's release workflow built the archive from a specific commit. To check an archive you downloaded from the release page, install the [GitHub CLI](https://cli.github.com/) and run:

```sh
gh attestation verify engineering-workshop.tar.gz --repo ShmalexM/ml-workshop
```

Use `engineering-workshop.zip` for the Windows archive. Releases published before the workflow added attestations have none, so the command fails for them.

## Report a vulnerability

Report vulnerabilities privately with the repository's [private reporting form](https://github.com/ShmalexM/ml-workshop/security/advisories/new). It is also on the [Security advisories](https://github.com/ShmalexM/ml-workshop/security/advisories) page under **Report a vulnerability**. Include the steps to reproduce, your operating system, and whether you used the install command or a clone. Do not include personal notes, progress databases, credentials, or sensitive source code in public issues. There is no guaranteed response time.

For a bug that is not a security problem, use the [bug report form](https://github.com/ShmalexM/ml-workshop/issues/new?template=bug_report.yml).

## Personal data

Project catalogs, local paths and notes are personal data. The application does not scan referenced repositories, and `data/` is ignored by Git. Progress exports include project metadata and should be reviewed before sharing. The app keeps the 10 newest exports in `data/backups` and deletes older ones that it made; it does not delete other files in that folder. Node VM contexts do not isolate untrusted code from the host.
