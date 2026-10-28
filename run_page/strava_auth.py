"""Load private local credentials and preserve refreshed Strava tokens."""

import json
import os
import base64
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
TOKEN_CACHE = ROOT / ".github" / "strava-token.enc"


def _binding(client_id, refresh_token):
    return f"{client_id}:{hashlib.sha256(refresh_token.encode()).hexdigest()}"


def _cipher_key(client_secret):
    return hashlib.sha256(
        b"gux-workouts/strava-token/v1:" + client_secret.encode()
    ).digest()


def cached_refresh_token(client_id, client_secret, refresh_token):
    if not TOKEN_CACHE.exists():
        return refresh_token
    from Crypto.Cipher import AES

    record = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
    binding = _binding(client_id, refresh_token)
    # Changing the initial Secret deliberately resets the encrypted token chain.
    if record.get("binding") != binding:
        return refresh_token
    if record.get("version") != 1:
        raise ValueError("Unsupported Strava token cache version")
    cipher = AES.new(
        _cipher_key(client_secret),
        AES.MODE_GCM,
        nonce=base64.b64decode(record["nonce"]),
    )
    cipher.update(binding.encode())
    plaintext = cipher.decrypt_and_verify(
        base64.b64decode(record["ciphertext"]), base64.b64decode(record["tag"])
    )
    return json.loads(plaintext)["refresh_token"]


def refresh_tokens(client, client_id, client_secret, refresh_token):
    response = client.refresh_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=cached_refresh_token(client_id, client_secret, refresh_token),
    )
    save_tokens(response, client_id, client_secret, refresh_token)
    return response


def load_local_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def save_tokens(tokens, client_id=None, client_secret=None, initial_refresh_token=None):
    """Never print credentials or put them in tracked files."""
    updates = {
        "STRAVA_ACCESS_TOKEN": tokens["access_token"],
        "STRAVA_CLIENT_REFRESH_TOKEN": tokens["refresh_token"],
    }
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8-sig").splitlines()
        remaining = dict(updates)
        result = []
        for line in lines:
            key = line.split("=", 1)[0].strip()
            if key in remaining:
                result.append(f"{key}={remaining.pop(key)}")
            elif key not in updates:
                result.append(line)
        result.extend(f"{key}={value}" for key, value in remaining.items())
        temporary = ENV_FILE.with_suffix(".tmp")
        temporary.write_text("\n".join(result) + "\n", encoding="utf-8")
        temporary.replace(ENV_FILE)
    # GitHub's job token cannot update repository Secrets. Persist rotation using
    # authenticated encryption keyed by the high-entropy client secret instead.
    # The repository contains ciphertext only; no extra GitHub access token is needed.
    if os.environ.get("GITHUB_ACTIONS") == "true" and client_secret:
        from Crypto.Cipher import AES

        binding = _binding(client_id, initial_refresh_token)
        cipher = AES.new(_cipher_key(client_secret), AES.MODE_GCM)
        cipher.update(binding.encode())
        ciphertext, tag = cipher.encrypt_and_digest(
            json.dumps({"refresh_token": tokens["refresh_token"]}).encode()
        )
        record = {
            "version": 1,
            "binding": binding,
            "nonce": base64.b64encode(cipher.nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "tag": base64.b64encode(tag).decode(),
        }
        TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        temporary = TOKEN_CACHE.with_suffix(".tmp")
        temporary.write_text(json.dumps(record) + "\n", encoding="utf-8")
        temporary.replace(TOKEN_CACHE)
    os.environ.update(updates)
