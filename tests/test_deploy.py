"""Static checks for the Vikunja deployment files. Run: python3 -m unittest discover -s tests -v

There is no Docker on the machines this is written on, so these read the files as text: they
cannot prove the stack starts (that is the first deploy on the NAS), only that it cannot be
deployed carelessly: an unpinned image, a port open to the network, registration left on,
a secret committed, a service without a memory limit, a CRLF script on the NAS.
"""

import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8", newline="") as f:
        return f.read()


def service_blocks(compose):
    """name -> text of each service under `services:` (two-space indented keys)."""
    body = compose.split("\nservices:\n", 1)[1]
    parts = re.split(r"(?m)^  ([a-z][a-z0-9_-]*):\s*$", body)
    return dict(zip(parts[1::2], parts[2::2]))


class Compose(unittest.TestCase):
    def setUp(self):
        self.compose = read("compose.yaml")
        self.services = service_blocks(self.compose)

    def test_there_is_a_vikunja_service(self):
        self.assertIn("vikunja", self.services)

    def test_every_image_is_pinned_to_a_full_version(self):
        images = re.findall(r"(?m)^\s+image:\s*(\S+)", self.compose)
        self.assertTrue(images)
        for image in images:
            self.assertRegex(image, r":\d+\.\d+\.\d+$", f"{image} is not pinned to x.y.z")

    def test_ports_are_published_on_loopback_only(self):
        # The NAS reverse proxy is the only way in; a bare "3456:3456" would also open the LAN.
        ports = re.findall(r'(?m)^\s+-\s*"?(\d[^"\s]*:\d+(?::\d+)?)"?\s*$', self.compose)
        self.assertTrue(ports)
        for port in ports:
            self.assertTrue(port.startswith("127.0.0.1:"), f"{port} is not bound to 127.0.0.1")

    def test_registration_is_off_and_totp_is_on(self):
        self.assertRegex(self.compose, r'VIKUNJA_SERVICE_ENABLEREGISTRATION:\s*"false"')
        self.assertRegex(self.compose, r'VIKUNJA_SERVICE_ENABLETOTP:\s*"true"')

    def test_rate_limiting_is_on(self):
        self.assertRegex(self.compose, r'VIKUNJA_RATELIMIT_ENABLED:\s*"true"')

    def test_every_service_has_a_memory_limit_and_restarts(self):
        for name, block in self.services.items():
            self.assertRegex(block, r"(?m)^    mem_limit:\s*\d+[mg]$", f"{name}: no mem_limit")
            self.assertRegex(block, r"(?m)^    restart:\s*unless-stopped$", f"{name}: no restart")

    def test_data_lives_in_bind_mounts_under_data_and_backups(self):
        mounts = re.findall(r"(?m)^\s+-\s*(\./\S+?):/", self.compose)
        self.assertTrue(mounts)
        for mount in mounts:
            self.assertRegex(mount, r"^\./(data|backups)(/|$)", mount)

    def test_the_container_user_comes_from_the_env_file(self):
        # DSM owns the folders by its own user (1026:100 for the first one), not by 1000: a fixed
        # user in this file made the first deploy fail with "permission denied".
        self.assertRegex(self.compose, r'(?m)^\s+user:\s*"\$\{VIKUNJA_UID:\?[^}]+\}:\$\{VIKUNJA_GID:\?[^}]+\}"$')

    def test_secrets_come_from_the_env_file_not_the_compose_file(self):
        self.assertRegex(self.compose, r"(?m)^\s+env_file:\s*\.env$")
        self.assertNotRegex(self.compose, r"VIKUNJA_SERVICE_SECRET")


class EnvFile(unittest.TestCase):
    def test_the_example_names_every_required_setting_with_placeholders(self):
        example = read(".env.example")
        for key in ("VIKUNJA_SERVICE_PUBLICURL", "VIKUNJA_SERVICE_SECRET", "VIKUNJA_SERVICE_TIMEZONE"):
            self.assertRegex(example, rf"(?m)^{key}=", key)
        self.assertRegex(example, r"(?m)^VIKUNJA_SERVICE_SECRET=change-me")

    def test_the_example_has_numeric_ids_for_the_container_user(self):
        example = read(".env.example")
        self.assertRegex(example, r"(?m)^VIKUNJA_UID=\d+$")
        self.assertRegex(example, r"(?m)^VIKUNJA_GID=\d+$")

    def test_the_real_env_file_and_the_data_are_not_tracked(self):
        ignore = read(".gitignore").splitlines()
        for entry in (".env", "data/", "backups/"):
            self.assertIn(entry, ignore)


class Scripts(unittest.TestCase):
    def test_backup_script_is_strict_and_keeps_two_weeks(self):
        script = read("scripts/backup.sh")
        self.assertTrue(script.startswith("#!/usr/bin/env bash\n"))
        self.assertIn("set -euo pipefail", script)
        self.assertIn("-mtime +14", script)

    def test_backup_script_works_with_docker_compose_v1_and_v2(self):
        # DSM's Container Manager may only have the hyphenated command.
        script = read("scripts/backup.sh")
        self.assertIn("docker-compose", script)
        self.assertIn("docker compose version", script)

    @unittest.skipUnless(shutil.which("bash"), "no bash")
    def test_backup_script_parses(self):
        done = subprocess.run(["bash", "-n", os.path.join(ROOT, "scripts", "backup.sh")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)


class Hygiene(unittest.TestCase):
    def test_text_files_use_lf(self):
        for dirpath, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "data", "backups", "__pycache__")]
            for name in files:
                if name.endswith((".pyc", ".zip")):
                    continue
                with open(os.path.join(dirpath, name), "rb") as f:
                    self.assertNotIn(b"\r\n", f.read(), os.path.join(dirpath, name))

    def test_no_real_looking_secret_is_committed(self):
        for name in ("compose.yaml", ".env.example", "README.md", "scripts/backup.sh"):
            self.assertNotRegex(read(name), r"[A-Za-z0-9+/]{40,}", name)


if __name__ == "__main__":
    unittest.main()
