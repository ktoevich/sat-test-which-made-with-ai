from app.security import (
    hash_password,
    needs_rehash,
    new_token,
    temporary_password,
    token_fingerprint,
    verify_password,
)

ITERATIONS = 1_000


def test_a_hash_verifies_its_own_password():
    stored = hash_password("correct horse", iterations=ITERATIONS)
    assert verify_password("correct horse", stored)


def test_a_hash_rejects_the_wrong_password():
    stored = hash_password("correct horse", iterations=ITERATIONS)
    assert not verify_password("wrong horse", stored)


def test_the_password_is_not_recoverable_from_the_hash():
    stored = hash_password("hunter2", iterations=ITERATIONS)
    assert "hunter2" not in stored


def test_the_same_password_hashes_differently_each_time():
    first = hash_password("same", iterations=ITERATIONS)
    second = hash_password("same", iterations=ITERATIONS)
    assert first != second, "each hash must use a fresh salt"
    assert verify_password("same", first) and verify_password("same", second)


def test_malformed_hashes_are_rejected_rather_than_crashing():
    for stored in ("", "nonsense", "md5$1$aa$bb", "pbkdf2_sha256$notanint$aa$bb"):
        assert not verify_password("anything", stored)


def test_needs_rehash_flags_weaker_settings():
    assert needs_rehash(hash_password("x", iterations=100), iterations=1_000)
    assert not needs_rehash(hash_password("x", iterations=1_000), iterations=1_000)
    assert needs_rehash("md5$1$aa$bb", iterations=1_000)


def test_tokens_are_unique_and_stored_only_as_a_fingerprint():
    token = new_token()
    assert token != new_token()
    fingerprint = token_fingerprint(token)
    assert token not in fingerprint
    assert fingerprint == token_fingerprint(token)


def test_temporary_passwords_avoid_ambiguous_characters():
    for _ in range(20):
        assert not set(temporary_password()) & set("0O1lI")
