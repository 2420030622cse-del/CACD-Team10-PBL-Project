import string

def get_charset(ptype):
    """Returns the character set corresponding to the password type."""
    if ptype == 'PIN':
        return string.digits
    elif ptype == 'TEXT':
        return string.ascii_letters
    elif ptype == 'MIX':
        # Alphanumeric + standard special symbols
        return string.ascii_letters + string.digits + "!@#$%^&*"
    return string.ascii_letters

def index_to_string(index, charset, length):
    """Map an index to the matching fixed-length string in charset order."""
    base = len(charset)
    result = []
    temp = index
    for _ in range(length):
        result.append(charset[temp % base])
        temp //= base
    return "".join(reversed(result))

def generate_brute_force_batch(ptype, target_password, state=None, batch_size=500, charset=None):
    """
    Generate a deterministic batch for the exact configured password length.
    Shorter passwords are not tested before the target length, because a PIN
    should be evaluated as a strict 6-digit candidate set rather than every
    shorter length first.
    """
    charset = ''.join(dict.fromkeys(charset or get_charset(ptype)))
    if not charset:
        return [], False, {'index': 0, 'length': len(target_password), 'max_length': len(target_password), 'exhausted': True, 'attempts': 0}, 0

    target_length = len(target_password)
    base = len(charset)
    state = state or {}
    index = state.get('index', 0)
    length = state.get('length', target_length)
    total_attempts = state.get('attempts', 0)

    if length != target_length:
        length = target_length
        index = 0

    max_candidates = base ** target_length
    guesses = []
    found = False

    while len(guesses) < batch_size and index < max_candidates and not found:
        guess = index_to_string(index, charset, target_length)
        guesses.append(guess)
        index += 1
        total_attempts += 1
        found = guess == target_password

    exhausted = index >= max_candidates and not found
    next_state = {
        'index': index,
        'length': target_length,
        'max_length': target_length,
        'attempts': total_attempts,
        'exhausted': exhausted,
    }

    return guesses, found, next_state, len(guesses)
