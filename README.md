# vikunja

Vikunja, the task board for Stella Rain and Kade's other projects, deployed on a Synology
DS220+ with `docker compose` (Container Manager). GitHub issues stay the source of truth; this
is where they are looked at (plan: `stella-rain/app`, `docs/plans/`).

## Files

| Path | What |
|---|---|
| `compose.yaml` | The one service, pinned image, bind mounts, loopback port, memory limit |
| `.env.example` | The three settings to copy into `.env` on the NAS |
| `scripts/backup.sh` | A dump into `backups/`, older than 14 days deleted |
| `tests/test_deploy.py` | Static checks: pinned image, loopback port, registration off, no secret |

`data/`, `backups/` and `.env` exist only on the NAS and are never committed.

## Deploy on the NAS (DSM 7.2 or later, Container Manager)

1. Copy this folder to `/volume1/docker/vikunja` (File Station or `git clone`).
2. `cp .env.example .env`; set `VIKUNJA_SERVICE_PUBLICURL` to the HTTPS address you will serve,
   and `VIKUNJA_SERVICE_SECRET` to `openssl rand -hex 32`. Run `id` over SSH as the user who
   owns the folder and put its numbers in `VIKUNJA_UID` and `VIKUNJA_GID` (DSM: 1026 and 100).
3. Create the data folders as that same user, so they are already writable:
   `mkdir -p data/db data/files backups`. Check with `ls -ln`; the owner must match the two
   numbers. (A container user that does not own the folders restarts in a loop with
   "permission denied" in `docker-compose logs`.)
4. Container Manager, Project, Create: path `/volume1/docker/vikunja`, use the existing
   `compose.yaml`, start.
5. Reverse proxy: Control Panel, Login Portal, Advanced, Reverse Proxy, Create. Source HTTPS,
   your subdomain, port 443. Destination HTTP, `localhost`, port 3456. Certificate: the
   subdomain's own (Security, Certificate; Let's Encrypt is built in).
6. Router: forward only 443 to the NAS. **Never forward 3456**; the compose file binds it to
   the loopback address on purpose.

## First start

Registration is off, so create the one user from the command line, then sign in and turn on
two-factor authentication in the settings (it is enabled in the compose file):

    docker-compose exec vikunja /app/vikunja/vikunja user create --help

(`docker compose` with a space on newer installs.) Use the options it lists (username, email, password). From an iPhone, open the address in
Safari and use Share, Add to Home Screen.

## Security of a board on the internet

- Registration off, two-factor on, rate limiting on (compose file); the tests check all three.
- Only the NAS reverse proxy reaches Vikunja. In DSM, turn on Auto Block (Security, Protection)
  and keep DSM and Container Manager updated.
- API tokens for the sync service are created in Vikunja's settings, one per use, and kept
  only in that service's environment.

## Backups

`scripts/backup.sh` writes a dump (settings, database, files). Schedule it in Control Panel,
Task Scheduler, as a user-defined script from the project folder, daily, and copy `backups/`
off the NAS (Hyper Backup or a copy task to another machine). **A backup counts only after a
restore onto a second machine worked and the task count matched.** Try it once now.

## Upgrade

1. Read the Vikunja changelog for the new version.
2. Run `scripts/backup.sh`.
3. Change the tag in `compose.yaml` (a commit that says why), copy it to the NAS.
4. Container Manager, Project, Stop, then Build and Start. Migrations run on start.
5. To go back, restore the dump taken in step 2 and the old tag.

## Tests

    python3 -m unittest discover -s tests -v

They read the files as text. They cannot start the stack: the first deploy on the NAS is the
real test, and anything it shows goes into this README.
