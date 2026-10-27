from simulator.dictionary import COMMON_WORDS, get_common_passwords
from simulator.password_validator import validate_password

COMMON_3_DIGITS = ['123', '000', '111', '654', '456', '789', '987', '321', '012', '555', '777', '999', '147', '258', '369']
MIX_SUFFIXES = ['1234!', '12345!', '123456!', '2024!', '2025!', '2026!', '1234@', '!1234', '@1234']


def _mix_variants(password):
    forms = dict.fromkeys((password, password.lower(), password.capitalize(), password.upper()))
    for form in forms:
        yield form
        for suffix in MIX_SUFFIXES:
            yield form + suffix


def _text_variants(password):
    companions = COMMON_WORDS[:15]
    for first in (password.lower(), password.capitalize()):
        for second_word in companions:
            for second in (second_word.lower(), second_word.capitalize()):
                yield first + second

def generate_hybrid_batch(ptype, target_password, state, batch_size=500):
    """
    Generates a batch of hybrid attack attempts.
    
    State holds:
        - index1: index of first component
        - index2: index of second component
        - mode: current combination pattern (0, 1, 2, 3, etc.)
    """
    if ptype == 'PIN':
        if not state:
            state = {'index1': 0, 'index2': 0, 'mode': 0}
        idx1 = state.get('index1', 0)
        idx2 = state.get('index2', 0)
        mode = state.get('mode', 0)
        guesses = []
        found = False
        while len(guesses) < batch_size and idx1 < len(COMMON_3_DIGITS) and not found:
            first = COMMON_3_DIGITS[idx1]
            second = COMMON_3_DIGITS[idx2]
            guess = first + second if mode == 0 else first + second[::-1]
            guesses.append(guess)
            found = guess == target_password
            mode += 1
            if mode >= 2:
                mode = 0
                idx2 += 1
            if idx2 >= len(COMMON_3_DIGITS):
                idx1 += 1
                idx2 = 0
        next_state = {'index1': idx1, 'index2': idx2, 'mode': mode}
    else:
        passwords = get_common_passwords()
        word_index = state.get('word_index', 0)
        variant_index = state.get('variant_index', 0)
        guesses = []
        found = False

        while len(guesses) < batch_size and word_index < len(passwords) and not found:
            variants = _mix_variants(passwords[word_index]) if ptype == 'MIX' else _text_variants(passwords[word_index])
            for current_variant, guess in enumerate(variants):
                if current_variant < variant_index:
                    continue
                variant_index = current_variant + 1
                if not validate_password(guess, ptype)[0]:
                    continue
                guesses.append(guess)
                if guess == target_password:
                    found = True
                    break
                if len(guesses) >= batch_size:
                    break

            else:
                word_index += 1
                variant_index = 0
                continue

            if not found and len(guesses) >= batch_size:
                break
            if found:
                break
            word_index += 1
            variant_index = 0

        next_state = {
            'word_index': word_index,
            'variant_index': variant_index,
            'exhausted': word_index >= len(passwords) and not found,
        }

    checked_count = len(guesses)
    # Sample guesses for the UI log
    sample = guesses
    if len(guesses) > 15:
        sample = [guesses[round(i * (len(guesses) - 1) / 14)] for i in range(15)]
    return sample, found, next_state, checked_count
