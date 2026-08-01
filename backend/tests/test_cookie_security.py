from app.auth.security import generate_opaque_token, hash_opaque_token


def test_opaque_session_tokens_are_not_stored_verbatim() -> None:
    token = generate_opaque_token()

    assert len(token) >= 32
    assert hash_opaque_token(token) != token
    assert len(hash_opaque_token(token)) == 64
