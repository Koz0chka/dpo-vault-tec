"""
Генератор паролей.

Набор символов и длина настраиваются клиентом. Реализация — на
secrets.SystemRandom (КГПСЧ ОС), что гарантирует криптостойкость.
"""
from __future__ import annotations

import secrets
import string
from dataclasses import dataclass


@dataclass(frozen=True)
class PasswordPolicy:
    length: int = 16
    use_lower: bool = True
    use_upper: bool = True
    use_digits: bool = True
    use_symbols: bool = True
    avoid_ambiguous: bool = False  # не использовать 0/O/l/I/1 и т.п.


AMBIGUOUS = set("Il1O0o`'\"|{}[]()")

SYMBOLS = "!@#$%^&*-_=+?.,;:"


def _alphabet(policy: PasswordPolicy) -> str:
    chars: list[str] = []
    if policy.use_lower:
        chars.append(string.ascii_lowercase)
    if policy.use_upper:
        chars.append(string.ascii_uppercase)
    if policy.use_digits:
        chars.append(string.digits)
    if policy.use_symbols:
        chars.append(SYMBOLS)
    alphabet = "".join(chars)
    if policy.avoid_ambiguous:
        alphabet = "".join(c for c in alphabet if c not in AMBIGUOUS)
    return alphabet


def estimate_strength(password: str) -> str:
    """Грубая оценка стойкости пароля (для подсказки в UI)."""
    pool = 0
    if any(c in string.ascii_lowercase for c in password):
        pool += 26
    if any(c in string.ascii_uppercase for c in password):
        pool += 26
    if any(c in string.digits for c in password):
        pool += 10
    if any(c not in string.ascii_letters + string.digits for c in password):
        pool += 24
    if pool == 0:
        return "weak"
    import math
    entropy = len(password) * math.log2(pool)
    if entropy < 40:
        return "weak"
    if entropy < 60:
        return "medium"
    if entropy < 80:
        return "strong"
    return "very-strong"


def generate_password(policy: PasswordPolicy) -> str:
    """Генерирует один пароль по заданной политике."""
    alphabet = _alphabet(policy)
    if not alphabet:
        raise ValueError("Должен быть выбран хотя бы один набор символов")
    if policy.length < 4:
        raise ValueError("Длина пароля должна быть не меньше 4")

    rng = secrets.SystemRandom()
    # Гарантируем хотя бы по одному символу из каждого выбранного набора.
    result: list[str] = []
    required: list[str] = []
    if policy.use_lower:
        required.append(rng.choice(string.ascii_lowercase))
    if policy.use_upper:
        required.append(rng.choice(string.ascii_uppercase))
    if policy.use_digits:
        required.append(rng.choice(string.digits))
    if policy.use_symbols:
        required.append(rng.choice(SYMBOLS))

    if policy.avoid_ambiguous:
        required = [c for c in required if c not in AMBIGUOUS]

    remaining = max(0, policy.length - len(required))
    for _ in range(remaining):
        result.append(rng.choice(alphabet))

    result.extend(required)
    rng.shuffle(result)
    pwd = "".join(result[: policy.length])
    return pwd
