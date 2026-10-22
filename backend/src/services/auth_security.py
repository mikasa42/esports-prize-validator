"""Hash de senha e tokens usando primitivas da biblioteca padrão."""
import hashlib
import hmac
import secrets

ITERATIONS = 600_000
SESSION_SECONDS = 8 * 60 * 60
COOKIE_NAME = 'tournament_session'


def hash_senha(senha):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), bytes.fromhex(salt), ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}'


def verificar_senha(senha, encoded):
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or int(iterations) != ITERATIONS:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', senha.encode('utf-8'), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError, AttributeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


# Usuários inexistentes também passam pelo mesmo custo de verificação.
DUMMY_HASH = hash_senha(secrets.token_urlsafe(32))
