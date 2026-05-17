"""Password helpers: Django hashers + legacy plaintext upgrade."""


def verify_and_upgrade_password(user, raw_password):
    """
    Verify password for AUTH_USER_MODEL. Supports Django-encoded hashes and legacy
    plaintext; upgrades plaintext to hash on successful login.
    """
    if raw_password is None or not user.password:
        return False
    if user.check_password(raw_password):
        return True
    if user.password == raw_password:
        user.set_password(raw_password)
        user.save(update_fields=["password"])
        return True
    return False
