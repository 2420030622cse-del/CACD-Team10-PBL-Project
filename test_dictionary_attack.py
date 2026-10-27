import unittest

from simulator.brute_force import generate_brute_force_batch, get_charset
from simulator.dictionary import generate_dictionary_batch, get_common_passwords, get_dictionary_list
from simulator.hybrid import generate_hybrid_batch
from simulator.password_validator import validate_password
from simulator.rule_based import apply_pin_rules, generate_rule_based_batch, generate_rule_based_batch_details, get_sampled_pins
from simulator.statistics import calculate_search_space


class DictionaryAttackTests(unittest.TestCase):
    def test_pin_validation_accepts_only_ascii_digits(self):
        self.assertTrue(validate_password('123456', 'PIN')[0])
        self.assertFalse(validate_password('١٢٣٤٥٦', 'PIN')[0])

    def test_text_and_mixed_passwords_match_brute_force_character_set(self):
        self.assertEqual(len(get_charset('TEXT')), 94)
        self.assertEqual(set(get_charset('TEXT')), set(''.join(chr(code) for code in range(33, 127))))
        self.assertEqual(get_charset('TEXT'), get_charset('MIX'))
        self.assertEqual(calculate_search_space('TEXT', 8), (94 ** 8, 94, 94))
        self.assertEqual(calculate_search_space('MIX', 8), (94 ** 8, 94, 94))

    def test_text_and_mixed_validation_rejects_unsearchable_characters(self):
        self.assertTrue(validate_password('Password123!', 'TEXT')[0])
        self.assertFalse(validate_password('Password 123!', 'TEXT')[0])
        self.assertFalse(validate_password('Password123!é', 'TEXT')[0])
        self.assertTrue(validate_password('Password1?', 'MIX')[0])
        self.assertFalse(validate_password('Password1😀', 'MIX')[0])

    def test_common_password_dataset_is_loaded(self):
        passwords = get_common_passwords()
        self.assertGreaterEqual(len(passwords), 10000)
        self.assertEqual(passwords[0], 'password')

    def test_mix_dictionary_contains_common_variations(self):
        words = get_dictionary_list('MIX')
        self.assertIn('Password1234!', words)
        self.assertTrue(all(validate_password(word, 'MIX')[0] for word in words))

    def test_text_dictionary_contains_common_word(self):
        words = get_dictionary_list('TEXT')
        self.assertIn('password', words)

    def test_dictionary_state_advances_after_match(self):
        guesses, found, state, count = generate_dictionary_batch('MIX', 'Password1234!', {'index': 0}, 10)
        self.assertTrue(found)
        self.assertGreater(state['index'], 0)
        self.assertIn('Password1234!', guesses)

    def test_bruteforce_state_advances_after_match(self):
        guesses, found, state, count = generate_brute_force_batch('TEXT', 'ba', {}, 10, 'ab')
        self.assertTrue(found)
        self.assertGreater(state['index'], 0)
        self.assertEqual(guesses, ['aa', 'ab', 'ba'])
        self.assertEqual(count, 3)

    def test_bruteforce_exhausts_without_skipping_candidates(self):
        guesses, found, state, count = generate_brute_force_batch('TEXT', 'ac', {}, 20, 'ab')
        self.assertFalse(found)
        self.assertTrue(state['exhausted'])
        self.assertEqual(guesses, ['aa', 'ab', 'ba', 'bb'])
        self.assertEqual(count, 4)

    def test_bruteforce_batch_returns_every_candidate_in_order(self):
        guesses, found, state, count = generate_brute_force_batch('PIN', '999999', {}, 30)
        self.assertFalse(found)
        self.assertEqual(count, 30)
        self.assertEqual(len(guesses), 30)
        self.assertEqual(guesses[:4], ['000000', '000001', '000002', '000003'])
        self.assertEqual(state['index'], 30)

    def test_bruteforce_order_continues_across_batches(self):
        state = {}
        candidates = []
        found = False
        while not found:
            guesses, found, state, count = generate_brute_force_batch('TEXT', 'aaa', state, 2, 'abc')
            candidates.extend(guesses)
        self.assertEqual(candidates, ['aaa'])
        self.assertEqual(state['attempts'], 1)

    def test_bruteforce_uses_exact_target_length_only(self):
        state = {}
        candidates = []
        found = False
        while not found:
            guesses, found, state, count = generate_brute_force_batch('PIN', '20514', state, 1000)
            candidates.extend(guesses)
        self.assertTrue(all(len(candidate) == 5 for candidate in candidates))
        self.assertIn('20514', candidates)
        self.assertEqual(state['length'], 5)

    def test_hybrid_mix_matches_single_word_pattern(self):
        guesses, found, state, count = generate_hybrid_batch('MIX', 'Password1234!', {}, 500)
        self.assertTrue(found)
        self.assertGreater(count, 0)
        self.assertIn('Password1234!', guesses)
        self.assertGreater(state['variant_index'], 0)

    def test_rule_based_pin_finds_common_pin(self):
        state = {}
        found = False
        guesses = []
        while not found:
            batch, found, state, count = generate_rule_based_batch('PIN', '112233', state, 5)
            guesses.extend(batch)
            self.assertGreater(count, 0)
        self.assertIn('112233', guesses)

    def test_rule_based_pin_reports_exhaustion(self):
        state = {}
        attempts = 0
        found = False
        while not state.get('exhausted'):
            guesses, found, state, count = generate_rule_based_batch('PIN', '1234567', state, 1000)
            attempts += count
            self.assertFalse(found)
        self.assertTrue(state['exhausted'])
        self.assertGreater(attempts, 10000)

    def test_rule_based_pin_finds_odd_even_pattern_and_counts_batches(self):
        state = {}
        attempts = 0
        found = False
        while not found:
            guesses, found, state, count = generate_rule_based_batch('PIN', '135246', state, 3)
            attempts += count
            self.assertEqual(count, len(guesses))
            self.assertGreater(state['word_index'], 0)
        self.assertIn('135246', guesses)
        self.assertGreater(attempts, 3)

    def test_rule_based_pin_counts_past_ten_thousand_before_finding_ranked_pin(self):
        target = get_sampled_pins()[-1]
        state = {}
        attempts = 0
        found = False
        while not found:
            guesses, found, state, count = generate_rule_based_batch('PIN', target, state, 500)
            attempts += count
            if state['exhausted']:
                break
        self.assertTrue(found)
        self.assertIn(target, guesses)
        self.assertGreater(attempts, 10000)

    def test_rule_based_pin_applies_controlled_transformations(self):
        guesses = apply_pin_rules('1234')
        for candidate in ('1235', '1236', '4321', '1111', '01234', '12340'):
            self.assertIn(candidate, guesses)

    def test_rule_based_text_returns_base_and_exact_rules(self):
        records, found, state, count, match = generate_rule_based_batch_details(
            'TEXT', 'Password123', {}, 500, ['capitalize', 'number_suffix'], 2
        )
        self.assertTrue(found)
        self.assertEqual(match['candidate'], 'Password123')
        self.assertEqual(match['base_word'], 'password')
        self.assertEqual(match['rules'], ['capitalize', 'appendNumber(123)'])
        self.assertEqual(match['attempt'], state['attempts'])

    def test_rule_based_mixed_supports_configured_three_rule_candidates(self):
        records, found, state, count, match = generate_rule_based_batch_details(
            'MIX', 'p@ssword123!', {}, 1000, ['substitution', 'number_suffix', 'symbol_suffix'], 3
        )
        self.assertTrue(found)
        self.assertEqual(match['candidate'], 'p@ssword123!')
        self.assertEqual(match['base_word'], 'password')
        self.assertEqual(match['rules'], ['replace(a,@)', 'appendNumber(123)', 'appendSymbol(!)'])

    def test_rule_based_deduplicates_candidates_across_base_words(self):
        from unittest.mock import patch

        state = {}
        candidates = []
        with patch('simulator.rule_based.get_base_elements', return_value=['password', 'Password']):
            while not state.get('exhausted'):
                records, found, state, count, match = generate_rule_based_batch_details(
                    'TEXT', 'not-a-candidate', state, 1000, ['lowercase', 'capitalize'], 2
                )
                candidates.extend(record['candidate'] for record in records)
        self.assertEqual(len(candidates), len(set(candidates)))


if __name__ == '__main__':
    unittest.main()
