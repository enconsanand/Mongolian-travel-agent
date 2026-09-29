from bcrypt import checkpw, gensalt, hashpw


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    return hashpw(password.encode(), gensalt()).decode()
