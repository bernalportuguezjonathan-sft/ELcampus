import bcrypt

# bcrypt trunca en 72 bytes; cortamos explícito para que una clave larga
# no reviente en vez de fallar silenciosamente.
_MAX_BYTES = 72


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:_MAX_BYTES], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode()[:_MAX_BYTES], password_hash.encode())
