# vikunja

Deployment of Vikunja (the task board) on Kade's Synology DS220+ with `docker compose`:
the compose file, its settings template, a backup script and static checks. No application
code. Follow the `kade-workflow` skill; where it and this file differ, this file wins.
The plan and the reasons are in `stella-rain/app`, `docs/plans/` (GitHub issues stay the
source of truth; Vikunja is the board).

## Hard rules

- No secret, token, real address or personal email in any tracked file. Real settings live in
  `.env` on the NAS; `.env.example` holds placeholders. `data/`, `backups/` and `.env` are
  never committed.
- Every image is pinned to a full `x.y.z` tag, never `latest`, `unstable` or a bare major. An
  upgrade is its own commit with the changelog read and a backup taken first (README, "Upgrade").
- The only way in is the NAS reverse proxy: the port is published on `127.0.0.1` only, registration
  stays off, two-factor and rate limiting stay on. The static checks enforce these.
- Every service has `mem_limit` and `restart: unless-stopped`; the NAS is shared with DSM.
- A backup is real only after a restore on a second machine worked; do not call it done before.
- New module, crate or dependency: decide it with Kade first (options, trade-offs for long-term release maintainability, your recommendation). A second service in `compose.yaml`, a new image or a new script language is one.

## Layout

| Path | What |
|---|---|
| `compose.yaml` | The service, pinned image, bind mounts under `data/` and `backups/` |
| `.env.example` | Settings to copy to `.env` on the NAS |
| `scripts/backup.sh` | Dump into `backups/`, keep 14 days |
| `tests/test_deploy.py` | Static checks of the files above (stdlib only) |
| `.github/workflows/test.yml` | Runs the checks on push and pull request |

## Gates

| Part | Gate |
|---|---|
| Any file | `python3 -m unittest discover -s tests -v` |
| `compose.yaml` | The checks cannot start the stack: the deploy on the NAS is the gate. Without Docker here, say `NOT VERIFIED: docker compose config: no Docker on this machine` |
| `scripts/backup.sh` | `bash -n`, run by the checks; the real run and the restore are Kade's on the NAS |
| `CLAUDE.md` | At most 100 lines |
| Line endings | `.gitattributes` keeps `* text=auto eol=lf`; the checks fail on CRLF |

Anything that needs the NAS (deploy, reverse proxy, backup, restore, upgrade) is Kade's: name it
in the commit body as `NOT VERIFIED: <step>: needs the NAS`.

## State and version control

- Work is tracked in `stella-rain/app` issues; there is no `MEMORY.md` and no handoff file.
  What a change did, what was verified and the wrong turns: the commit body.
- **Local sessions** (on Kade's PC): commit each finished task to `main` automatically; Kade
  pushes. This repository is private.
- Author: `Kade <23338687+enjay27@users.noreply.github.com>`. No other email in commits or git config.

## Never commit

- `.env`, `data/`, `backups/`, dumps, API tokens, certificates, router or DNS details.
