import re

def validate_pin(password):
    """Validates if the password is a valid PIN (6 digits)."""
    reqs = [
        {"desc": "Exactly 6 characters", "status": len(password) == 6},
        {"desc": "Numbers 0–9 only", "status": re.fullmatch(r'[0-9]+', password) is not None}
    ]
    is_valid = all(r["status"] for r in reqs)
    return is_valid, reqs

def validate_text(password):
    """Validates an 8-20 character printable-ASCII password containing a letter."""
    reqs = [
        {"desc": "8–20 characters", "status": 8 <= len(password) <= 20},
        {"desc": "At least one letter", "status": re.search(r'[a-zA-Z]', password) is not None},
        {"desc": "Printable ASCII only (no spaces)", "status": re.fullmatch(r'[\x21-\x7E]+', password) is not None}
    ]
    is_valid = all(r["status"] for r in reqs)
    return is_valid, reqs

def validate_mix(password):
    """Validates if the password is a valid MIX (complex combinations)."""
    letter_count = sum(1 for c in password if c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
    digit_count = sum(1 for c in password if c in '0123456789')
    letter_digit_count = sum(1 for c in password if c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    symbol_count = len(password) - letter_digit_count

    reqs = [
        {"desc": "8–20 characters", "status": 8 <= len(password) <= 20},
        {"desc": "At least 1 letter", "status": letter_count >= 1},
        {"desc": "At least 1 number", "status": digit_count >= 1},
        {"desc": "At least 1 symbol", "status": symbol_count >= 1},
        {"desc": "Printable ASCII only (no spaces)", "status": re.fullmatch(r'[\x21-\x7E]+', password) is not None}
    ]
    is_valid = all(r["status"] for r in reqs)
    return is_valid, reqs

def validate_password(password, ptype):
    """
    Validates a password based on its type.
    Returns:
        tuple: (is_valid, list of requirements with their boolean status)
    """
    if ptype == 'PIN':
        return validate_pin(password)
    elif ptype == 'TEXT':
        return validate_text(password)
    elif ptype == 'MIX':
        return validate_mix(password)
    else:
        return False, [{"desc": "Unknown password type", "status": False}]
