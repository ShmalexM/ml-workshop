# Security

Engineering Workshop is a **trusted local Python and JavaScript runner** for one person. Exercise code runs with that person's filesystem and network permissions. Time/output limits and a temporary directory do not make it a sandbox. Do not expose the server publicly, run it as an administrator, or execute code you do not trust.

The server binds to loopback, validates Host and Origin, rejects cross-site requests, and requires a per-session token for writes. No account or API key is needed. Framework packages are installed during setup; exercise code and learner state stay local unless you explicitly share them.

Report vulnerabilities privately through the repository's [Security advisories](https://github.com/ShmalexM/ml-workshop/security/advisories) page using **Report a vulnerability**. Do not include personal notes, progress databases, credentials, or sensitive source code in public issues. There is no guaranteed response time.

Project catalogs, local paths and notes are personal data. The application does not scan referenced repositories, and `data/` is ignored by Git. Progress exports include project metadata and should be reviewed before sharing. Node VM contexts do not isolate untrusted code from the host.
