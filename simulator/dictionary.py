from functools import lru_cache
from pathlib import Path

from simulator.password_validator import validate_password


DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
PASSWORD_LIST_PATH = DATA_DIR / '10k-most-common.txt'
PASSWORD_LIST_SOURCE = 'danielmiessler/SecLists Passwords/Common-Credentials/10k-most-common.txt'

COMMON_WORDS = [
    'password', 'admin', 'welcome', 'hello', 'security', 'qwerty', 'computer', 'football', 'letmein', 'test',
    'pass', 'root', 'login', 'user', 'monkey', 'dragon', 'secret', 'trust', 'oracle', '12345678', 'shadow',
    'system', 'manager', 'database', 'access', 'network', 'server', 'account', 'backup', 'control'
]

COMMON_PINS = [
    '1234', '0000', '1111', '1212', '7777', '2580', '4321', '6969', '1004', '4821',
    '123456', '654321', '000000', '111111', '112233', '010203', '123123', '222222', '333333', '555555',
    '987654', '101010', '159357', '147258', '369258', '852741', '102030', '135792', '024681', '135246'
]

DICTIONARY_FILES = {
    'PIN': DATA_DIR / 'pin_dictionary.txt',
    'TEXT': DATA_DIR / 'text_dictionary.txt',
    'MIX': DATA_DIR / 'mixed_dictionary.txt',
}

DEFAULT_DICTIONARIES = {
    'PIN': [
        '1234', '0000', '1111', '1212', '7777', '2580', '4321', '6969', '1004', '4821',
        '123456', '654321', '000000', '111111'
    ],
    'TEXT': [
        'admin', 'hello', 'password', 'welcome', 'student', 'college', 'computer', 'security', 'dragon',
        'sunshine', 'login', 'letmein'
    ],
    'MIX': [
        'Password1234!', 'password123', 'admin123', 'hello123', 'student2026', 'Welcome1', 'Password1!', 'Hello@123',
        'security2024', 'dragon!99', 'root@2025'
    ],
}


def _clean_entries(raw_lines):
    cleaned = []
    seen = set()
    duplicate_count = 0
    for line in raw_lines:
        candidate = line.strip()
        if not candidate or candidate.startswith('#'):
            continue
        if candidate in seen:
            duplicate_count += 1
            continue
        seen.add(candidate)
        cleaned.append(candidate)
    return cleaned, duplicate_count


@lru_cache(maxsize=1)
def get_common_passwords():
    """Read the bundled common-password list once, preserving ranking and removing duplicates."""
    if not PASSWORD_LIST_PATH.is_file():
        return tuple(DEFAULT_DICTIONARIES['TEXT'])

    passwords = []
    seen = set()
    with PASSWORD_LIST_PATH.open(encoding='utf-8-sig') as password_file:
        for line in password_file:
            password = line.strip()
            if password and not password.startswith('#') and password not in seen:
                passwords.append(password)
                seen.add(password)
    return tuple(passwords)


COMMON_WORDS = list(get_common_passwords())


def analyze_dictionary(ptype):
    """Return raw, duplicate, and usable counts for the dictionary selected by password type."""
    path = DICTIONARY_FILES.get(ptype, DICTIONARY_FILES['TEXT'])
    raw_lines = []
    if path.is_file():
        with path.open(encoding='utf-8-sig') as handle:
            raw_lines = handle.readlines()

    if not raw_lines:
        raw_lines = [f"{value}\n" for value in DEFAULT_DICTIONARIES.get(ptype, [])]

    cleaned, duplicate_count = _clean_entries(raw_lines)
    valid_candidates = [candidate for candidate in cleaned if validate_password(candidate, ptype)[0]]
    return {
        'raw_entries': sum(1 for line in raw_lines if line.strip() and not line.strip().startswith('#')),
        'duplicates_removed': duplicate_count,
        'usable_candidates': len(valid_candidates),
        'valid_candidates': valid_candidates,
        'dictionary_path': str(path),
    }


@lru_cache(maxsize=3)
def get_dictionary_list(ptype):
    """Return type-valid dictionary candidates while preserving order and case exactly as stored."""
    path = DICTIONARY_FILES.get(ptype, DICTIONARY_FILES['TEXT'])
    entries = []
    if path.is_file():
        with path.open(encoding='utf-8-sig') as handle:
            entries = [line.strip() for line in handle]
    if not entries:
        entries = DEFAULT_DICTIONARIES.get(ptype, [])

    cleaned, _ = _clean_entries(entries)
    return [candidate for candidate in cleaned if validate_password(candidate, ptype)[0]]


def generate_dictionary_batch(ptype, target_password, state, batch_size=500):
    """Generate a deterministic batch of dictionary candidates in the configured order."""
    words = get_dictionary_list(ptype)

    if not state:
        state = {'index': 0}

    index = state.get('index', 0)
    guesses = []
    found = False
    checked_count = 0

    while checked_count < batch_size and index < len(words) and not found:
        guess = words[index]
        guesses.append(guess)
        checked_count += 1

        if guess == target_password:
            found = True
            index += 1
            break

        index += 1

    guesses_sample = guesses
    if len(guesses) > 15:
        step = len(guesses) // 14
        guesses_sample = []
        for i in range(14):
            guesses_sample.append(guesses[i * step])
        if guesses[-1] not in guesses_sample:
            guesses_sample.append(guesses[-1])

    next_state = {'index': index, 'exhausted': index >= len(words) and not found}
    return guesses_sample, found, next_state, len(guesses)
