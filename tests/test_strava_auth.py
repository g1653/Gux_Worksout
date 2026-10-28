import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "run_page"))
import strava_auth  # noqa: E402


class StravaAuthTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        for name, value in (
            ("ENV_FILE", root / ".env"),
            ("TOKEN_CACHE", root / "token.enc"),
        ):
            patcher = patch.object(strava_auth, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.dict(os.environ, {}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_local_refresh_preserves_settings_and_writes_latest_tokens(self):
        strava_auth.ENV_FILE.write_text(
            "\ufeff# local settings\nSTRAVA_CLIENT_ID=123\nSTRAVA_CLIENT_REFRESH_TOKEN=old\n",
            encoding="utf-8",
        )
        strava_auth.save_tokens(
            {"access_token": "access-new", "refresh_token": "refresh-new"}
        )
        content = strava_auth.ENV_FILE.read_text()
        self.assertIn("# local settings", content)
        self.assertIn("STRAVA_CLIENT_ID=123", content)
        self.assertIn("STRAVA_CLIENT_REFRESH_TOKEN=refresh-new", content)
        self.assertIn("STRAVA_ACCESS_TOKEN=access-new", content)
        self.assertNotIn("old", content)
        self.assertFalse(strava_auth.TOKEN_CACHE.exists())

    def test_ci_uses_latest_encrypted_token_without_exposing_it(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        client = Mock()
        client.refresh_access_token.return_value = {
            "access_token": "access-one",
            "refresh_token": "refresh-one",
        }
        strava_auth.refresh_tokens(
            client, "123", "high-entropy-secret", "bootstrap-token"
        )
        serialized = strava_auth.TOKEN_CACHE.read_text()
        for sensitive in (
            "access-one",
            "refresh-one",
            "bootstrap-token",
            "high-entropy-secret",
        ):
            self.assertNotIn(sensitive, serialized)
        client.refresh_access_token.return_value = {
            "access_token": "access-two",
            "refresh_token": "refresh-two",
        }
        strava_auth.refresh_tokens(
            client, "123", "high-entropy-secret", "bootstrap-token"
        )
        self.assertEqual(
            client.refresh_access_token.call_args.kwargs["refresh_token"], "refresh-one"
        )
        self.assertEqual(
            strava_auth.cached_refresh_token(
                "123", "high-entropy-secret", "bootstrap-token"
            ),
            "refresh-two",
        )

    def test_new_secret_resets_cache_and_local_sync_can_use_pulled_cache(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        strava_auth.save_tokens(
            {"access_token": "a", "refresh_token": "r"}, "123", "secret", "initial"
        )
        self.assertEqual(
            strava_auth.cached_refresh_token("123", "secret", "reauthorized"),
            "reauthorized",
        )
        os.environ.pop("GITHUB_ACTIONS")
        self.assertEqual(
            strava_auth.cached_refresh_token("123", "secret", "initial"), "r"
        )

    def test_tampering_fails_before_any_refresh_request(self):
        os.environ["GITHUB_ACTIONS"] = "true"
        strava_auth.save_tokens(
            {"access_token": "a", "refresh_token": "r"}, "123", "secret", "initial"
        )
        record = json.loads(strava_auth.TOKEN_CACHE.read_text())
        record["tag"] = "AAAAAAAAAAAAAAAAAAAAAA=="
        strava_auth.TOKEN_CACHE.write_text(json.dumps(record))
        client = Mock()
        with self.assertRaises(ValueError):
            strava_auth.refresh_tokens(client, "123", "secret", "initial")
        client.refresh_access_token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
