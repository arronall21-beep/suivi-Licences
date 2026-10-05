"""Politique minimale de mot de passe : 8 caractères, au moins une lettre et un chiffre."""

MIN_LENGTH = 8
MAX_LENGTH = 128
POLICY_TEXT = f"{MIN_LENGTH} caractères minimum, avec au moins une lettre et un chiffre"


def validate_password(password: str, email: str | None = None) -> str:
    if len(password) < MIN_LENGTH:
        raise ValueError(f"Mot de passe trop court : {POLICY_TEXT}")
    if len(password) > MAX_LENGTH:
        raise ValueError(f"Mot de passe trop long ({MAX_LENGTH} caractères maximum)")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError(f"Mot de passe trop faible : {POLICY_TEXT}")
    if email and password.lower() in {email.lower(), email.split("@")[0].lower()}:
        raise ValueError("Le mot de passe ne doit pas être identique à l'adresse email")
    return password
