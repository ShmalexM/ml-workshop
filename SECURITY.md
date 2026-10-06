# Security

Engineering Workshop is a **trusted local Python and JavaScript runner** for one person. Exercise code runs with that person's filesystem and network permissions. Time/output limits and a temporary directory do not make it a sandbox. Do not expose the server publicly, run it as an administrator, or execute code you do not trust.

The server binds to loopback, validates Host and Origin, rejects cross-site requests, and requires a per-session token for writes. No account or API key is needed. Framework packages are installed during setup; exercise code and learner state stay local unless you explicitly share them.

## Report a vulnerability

Report vulnerabilities privately with the repository's [private reporting form](https://github.com/ShmalexM/ml-workshop/security/advisories/new). It is also on the [Security advisories](https://github.com/ShmalexM/ml-workshop/security/advisories) page under **Report a vulnerability**. Include the steps to reproduce, your operating system, and whether you used the install command or a clone. Do not include personal notes, progress databases, credentials, or sensitive source code in public issues. There is no guaranteed response time.

For a bug that is not a security problem, use the [bug report form](https://github.com/ShmalexM/ml-workshop/issues/new?template=bug_report.yml).

## Personal data

Project catalogs, local paths and notes are personal data. The application does not scan referenced repositories, and `data/` is ignored by Git. Progress exports include project metadata and should be reviewed before sharing. Node VM contexts do not isolate untrusted code from the host.
