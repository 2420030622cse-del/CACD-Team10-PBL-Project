import csv
import secrets
from collections import OrderedDict
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from simulator.dictionary import COMMON_PINS, COMMON_WORDS, get_common_passwords


PIN_SAMPLE_PATH = Path(__file__).resolve().parents[1] / '10k_6_digit_pins.csv'
PIN_DIGIT_ORDER = '1234567890'
PIN_PATTERN_SEEDS = [
    ''.join(PIN_DIGIT_ORDER[::2][:3] + PIN_DIGIT_ORDER[1::2][:3]),
    ''.join(PIN_DIGIT_ORDER[1::2][:3] + PIN_DIGIT_ORDER[::2][:3]),
]
BASE_PINS = list(dict.fromkeys([
    '1234', '1111', '0000', '1212', '9876', '123456', '000000', '1357', '2468', '1122',
] + COMMON_PINS + PIN_PATTERN_SEEDS))

DEFAULT_RULES = {
    'PIN': ['original', 'reverse', 'sequential', 'repeated', 'prefix_zero', 'suffix_zero', 'position'],
    'TEXT': ['original', 'lowercase', 'capitalize', 'uppercase', 'reverse', 'number_prefix', 'number_suffix', 'symbol_prefix', 'symbol_suffix', 'substitution'],
    'MIX': ['original', 'lowercase', 'capitalize', 'uppercase', 'reverse', 'number_prefix', 'number_suffix', 'symbol_prefix', 'symbol_suffix', 'substitution'],
}
RULE_ORDER = ['original', 'lowercase', 'capitalize', 'uppercase', 'reverse', 'number_prefix', 'number_suffix', 'symbol_prefix', 'symbol_suffix', 'substitution', 'sequential', 'repeated', 'prefix_zero', 'suffix_zero', 'position']
RULE_LABELS = {
    'original': 'Original',
    'lowercase': 'Lowercase',
    'capitalize': 'Capitalize',
    'uppercase': 'Uppercase',
    'reverse': 'Reverse digits',
    'number_prefix': 'Prefix number',
    'number_suffix': 'Append number',
    'symbol_prefix': 'Prefix symbol',
    'symbol_suffix': 'Append symbol',
    'substitution': 'Character substitution',
    'sequential': 'Sequential pattern',
    'repeated': 'Repeated digit pattern',
    'prefix_zero': 'Prefix 0',
    'suffix_zero': 'Append 0',
    'position': 'Change final digit',
}
SUBSTITUTIONS = [('a', '@'), ('e', '3'), ('i', '1'), ('o', '0'), ('s', '$')]
_SEEN_CANDIDATES_BY_RUN = OrderedDict()
_MAX_ACTIVE_RUNS = 32


def get_base_elements(ptype):
    """Return ranked base values used by the selected rule family."""
    if ptype == 'PIN':
        return BASE_PINS + list(get_sampled_pins())
    return list(get_common_passwords()) or COMMON_WORDS


@lru_cache(maxsize=1)
def get_sampled_pins():
    """Read ranked six-digit PIN seeds from the locally generated CSV."""
    if not PIN_SAMPLE_PATH.is_file():
        return ()

    pins = []
    seen = set()
    with PIN_SAMPLE_PATH.open(newline='', encoding='utf-8') as pin_file:
        for row in csv.DictReader(pin_file):
            pin = (row.get('pin') or '').strip()
            if len(pin) == 6 and pin.isdigit() and pin not in seen:
                pins.append(pin)
                seen.add(pin)
    return tuple(pins)


def _single_rule_candidates(base, ptype, rule):
    if rule == 'original':
        return [(base, 'original')]
    if rule == 'lowercase' and ptype != 'PIN':
        return [(base.lower(), 'lowercase')]
    if rule == 'capitalize' and ptype != 'PIN':
        return [(base.capitalize(), 'capitalize')]
    if rule == 'uppercase' and ptype != 'PIN':
        return [(base.upper(), 'uppercase')]
    if rule == 'reverse':
        return [(base[::-1], 'reverse')]
    if rule == 'number_prefix' and ptype != 'PIN':
        return [(f'1{base}', 'prefixNumber(1)'), (f'123{base}', 'prefixNumber(123)')]
    if rule == 'number_suffix' and ptype != 'PIN':
        return [(f'{base}1', 'appendNumber(1)'), (f'{base}123', 'appendNumber(123)')]
    if rule == 'symbol_prefix' and ptype != 'PIN':
        return [(f'@{base}', 'prefixSymbol(@)')]
    if rule == 'symbol_suffix' and ptype != 'PIN':
        return [(f'{base}!', 'appendSymbol(!)'), (f'{base}@', 'appendSymbol(@)')]
    if rule == 'substitution' and ptype != 'PIN':
        candidates = []
        for source, replacement in SUBSTITUTIONS:
            if source in base.lower():
                index = base.lower().index(source)
                candidates.append((base[:index] + replacement + base[index + 1:], f'replace({source},{replacement})'))
        return candidates
    if rule == 'sequential' and ptype == 'PIN' and base.isdigit():
        number = int(base)
        width = len(base)
        return [(str(number + offset).zfill(width), f'sequential(+{offset})') for offset in (1, 2) if number + offset < 10 ** width]
    if rule == 'repeated' and ptype == 'PIN' and base.isdigit():
        return [(digit * len(base), f'repeated({digit})') for digit in '0123456789']
    if rule == 'prefix_zero' and ptype == 'PIN' and base.isdigit():
        return [(f'0{base}', 'prefix(0)')]
    if rule == 'suffix_zero' and ptype == 'PIN' and base.isdigit():
        return [(f'{base}0', 'append(0)')]
    if rule == 'position' and ptype == 'PIN' and base.isdigit():
        return [(f'{base[:-1]}{digit}', f'replacePosition({len(base)},{digit})') for digit in '0123456789' if digit != base[-1:]]
    return []


def _ordered_rules(ptype, enabled_rules=None):
    requested = DEFAULT_RULES.get(ptype, []) if enabled_rules is None else enabled_rules
    ordered = []
    for rule in ['original', *requested]:
        if rule in DEFAULT_RULES.get(ptype, []) and rule not in ordered:
            ordered.append(rule)
    return ordered


def _base_candidates(base, ptype, enabled_rules, max_rules):
    rules = _ordered_rules(ptype, enabled_rules)
    seen = set()
    output = []

    def add(candidate, rule_names):
        if candidate not in seen:
            seen.add(candidate)
            output.append({'candidate': candidate, 'base_word': base, 'rules': rule_names})

    add(base, ['original'])
    transformations = [rule for rule in rules if rule != 'original']
    for rule in transformations:
        for candidate, label in _single_rule_candidates(base, ptype, rule):
            add(candidate, [label])

    if ptype != 'PIN':
        for rule_count in range(2, min(max_rules, len(transformations)) + 1):
            for rule_sequence in combinations(transformations, rule_count):
                variants = [(base, [])]
                for rule in rule_sequence:
                    transformed = []
                    for candidate, applied_rules in variants:
                        transformed.extend(
                            (next_candidate, applied_rules + [label])
                            for next_candidate, label in _single_rule_candidates(candidate, ptype, rule)
                        )
                    variants = transformed
                for candidate, applied_rules in variants:
                    add(candidate, applied_rules)
    return output


def get_word_variations(word, ptype):
    """Compatibility helper returning the current default candidate order."""
    return [entry['candidate'] for entry in _base_candidates(word, ptype, None, 2)]


def apply_pin_rules(base_str):
    return get_word_variations(base_str, 'PIN')


def apply_text_rules(base_word):
    return get_word_variations(base_word, 'TEXT')


def to_leetspeak(word):
    result = word
    for source, replacement in SUBSTITUTIONS:
        result = result.replace(source, replacement)
    return result


def apply_mix_rules(base_word):
    return get_word_variations(base_word, 'MIX')


def generate_rule_based_batch_details(ptype, target_password, state, batch_size=500, enabled_rules=None, max_rules=2):
    """Generate unique ordered candidates with base and transformation provenance."""
    base_elements = get_base_elements(ptype)
    state = state or {}
    word_idx = state.get('base_index', state.get('word_index', 0))
    var_idx = state.get('variation_index', 0)
    attempts = state.get('attempts', 0)
    run_id = state.get('run_id') or secrets.token_urlsafe(18)
    seen = _SEEN_CANDIDATES_BY_RUN.setdefault(run_id, set(state.get('seen_candidates', [])))
    _SEEN_CANDIDATES_BY_RUN.move_to_end(run_id)
    while len(_SEEN_CANDIDATES_BY_RUN) > _MAX_ACTIVE_RUNS:
        _SEEN_CANDIDATES_BY_RUN.popitem(last=False)
    records = []
    found_record = None

    while len(records) < batch_size and word_idx < len(base_elements):
        base = base_elements[word_idx]
        variations = _base_candidates(base, ptype, enabled_rules, max_rules)
        while var_idx < len(variations) and len(records) < batch_size:
            record = variations[var_idx]
            var_idx += 1
            candidate = record['candidate']
            if candidate in seen:
                continue
            seen.add(candidate)
            attempts += 1
            record = dict(record)
            record['attempt'] = attempts
            records.append(record)
            if candidate == target_password:
                found_record = record
                break
        if found_record:
            break
        if var_idx >= len(variations):
            word_idx += 1
            var_idx = 0

    next_state = {
        'word_index': word_idx + (1 if var_idx > 0 else 0),
        'base_index': word_idx,
        'variation_index': var_idx,
        'attempts': attempts,
        'run_id': run_id,
        'exhausted': word_idx >= len(base_elements) and not found_record,
    }
    if found_record or next_state['exhausted']:
        _SEEN_CANDIDATES_BY_RUN.pop(run_id, None)
    return records, found_record is not None, next_state, len(records), found_record


def generate_rule_based_batch(ptype, target_password, state, batch_size=500, enabled_rules=None, max_rules=2):
    """Legacy-compatible wrapper that returns sampled guess strings and state."""
    records, found, next_state, count, _ = generate_rule_based_batch_details(
        ptype, target_password, state, batch_size, enabled_rules, max_rules
    )
    sample = records
    if len(records) > 15:
        sample = [records[round(index * (len(records) - 1) / 14)] for index in range(15)]
    return [record['candidate'] for record in sample], found, next_state, count
