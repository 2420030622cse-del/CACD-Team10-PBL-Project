import os
import re
import unittest
from unittest.mock import patch

from app import app


class ApplicationApiTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SECRET_KEY='test-secret')
        self.client = app.test_client()

    def test_simulation_api_accepts_password_without_server_session(self):
        response = self.client.post('/api/simulate-step', json={
            'password': '123456',
            'method': 'brute_force',
            'type': 'PIN',
            'batch_size': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['guesses'], ['000000'])
        self.assertEqual(response.json['count'], 1)

    def test_simulation_api_rejects_invalid_configuration(self):
        response = self.client.post('/api/simulate-step', json={
            'password': '123456',
            'method': 'password_safety',
            'type': 'PIN',
        })
        self.assertEqual(response.status_code, 400)

    def test_sampled_hybrid_guesses_keep_their_true_attempt_numbers(self):
        response = self.client.post('/api/simulate-step', json={
            'password': '999999',
            'method': 'hybrid',
            'type': 'PIN',
            'batch_size': 20,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['count'], 20)
        self.assertEqual(
            response.json['guess_attempts'],
            [round(index * 19 / 14) + 1 for index in range(15)],
        )

    def test_method_comparison_matches_actual_brute_force_and_hybrid_order(self):
        response = self.client.post('/api/compare-methods', json={
            'password': '123123',
            'type': 'PIN',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['search_spaces'][0], 1_000_000)
        self.assertEqual(response.json['search_spaces'][3], 450)
        self.assertEqual(response.json['attempts_needed'][0], 123124)
        self.assertEqual(response.json['attempts_needed'][3], 1)
        self.assertTrue(response.json['found'][0])
        self.assertTrue(response.json['found'][3])

    def test_text_hybrid_comparison_uses_the_real_candidate_generator(self):
        from simulator.hybrid import generate_hybrid_batch

        password = 'Password1234!'
        _, found, _, actual_attempts = generate_hybrid_batch('MIX', password, {}, 5000)
        self.assertTrue(found)
        response = self.client.post('/api/compare-methods', json={
            'password': password,
            'type': 'MIX',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['found'][3])
        self.assertEqual(response.json['attempts_needed'][3], actual_attempts)

    def test_brute_force_progress_space_matches_exact_length_candidates(self):
        with patch('app.analyze_password_preview', return_value={'preview': {}}):
            validation = self.client.post('/api/validate', json={'password': '123456', 'type': 'PIN'})
        self.assertTrue(validation.json['is_valid'])
        response = self.client.get('/simulation?method=brute_force&type=PIN')
        match = re.search(r'window\.THEORETICAL_SPACE = parseInt\("(\d+)"\)', response.get_data(as_text=True))
        self.assertIsNotNone(match)
        self.assertEqual(int(match.group(1)), 1_000_000)

    def test_report_api_rejects_invalid_metrics(self):
        response = self.client.post('/api/report', json={
            'password': '123456',
            'method': 'brute_force',
            'type': 'PIN',
            'attempts': 'not-a-number',
        })
        self.assertEqual(response.status_code, 400)

    def test_report_api_generates_result_without_saving_password(self):
        ratings = {
            'security_strength': 7.0,
            'memorability': 6.0,
            'randomness': 7.0,
            'pattern_safety': 5.0,
            'typing_usability': 8.0,
            'overall_rating': 6.7,
        }
        with patch('app.predict_dimensions', return_value=ratings), \
                patch('app.identify_aspects', return_value={'strongest': {}, 'weakest': {}}), \
                patch('app.generate_ai_recommendation', return_value='Use a unique password.'), \
                patch('app.save_simulation') as save:
            response = self.client.post('/api/report', json={
                'password': '123456',
                'method': 'brute_force',
                'type': 'PIN',
                'attempts': 1,
                'time_taken': 0.2,
                'speed': 5,
                'found': True,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['ratings']['overall_rating'], 6.7)
        self.assertEqual(response.json['formatted_space'], '1.00 Million')
        self.assertNotIn('password', response.json)
        self.assertEqual(save.call_args.kwargs['result'], 'cracked')

    def test_cors_only_allows_configured_origins(self):
        with patch.dict(os.environ, {'CORS_ALLOWED_ORIGINS': 'https://example.github.io'}):
            allowed = self.client.options('/api/validate', headers={'Origin': 'https://example.github.io'})
            denied = self.client.options('/api/validate', headers={'Origin': 'https://other.example'})
        self.assertEqual(allowed.headers.get('Access-Control-Allow-Origin'), 'https://example.github.io')
        self.assertIsNone(denied.headers.get('Access-Control-Allow-Origin'))

    def test_cross_origin_validation_does_not_create_a_backend_password_session(self):
        with patch.dict(os.environ, {'CORS_ALLOWED_ORIGINS': 'https://example.github.io'}), \
                patch('app.analyze_password_preview', return_value={'preview': {}}):
            response = self.client.post(
                '/api/validate',
                json={'password': '123456', 'type': 'PIN'},
                headers={'Origin': 'https://example.github.io'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Access-Control-Allow-Origin'), 'https://example.github.io')
        self.assertNotIn('Set-Cookie', response.headers)

    def test_production_validation_never_stores_server_side_passwords(self):
        with patch('app.APP_ENV', 'production'), \
                patch('app.analyze_password_preview', return_value={'preview': {}}):
            response = self.client.post('/api/validate', json={'password': '123456', 'type': 'PIN'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_legacy_password_session_is_migrated_without_plaintext(self):
        with self.client.session_transaction() as browser_session:
            browser_session['test_password'] = '123456'
        response = self.client.get('/simulation?method=brute_force')
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as browser_session:
            self.assertIsNone(browser_session.get('test_password'))
            self.assertTrue(browser_session.get('test_password_token'))

    def test_stopped_simulation_recommendation_does_not_claim_resistance(self):
        from ai.recommendation_engine import generate_ai_recommendation

        ratings = {
            'security_strength': 5.0,
            'memorability': 5.0,
            'randomness': 5.0,
            'pattern_safety': 5.0,
            'typing_usability': 5.0,
        }
        recommendation = generate_ai_recommendation('A_long_test_password_2026!', ratings, {
            'method': 'Brute Force',
            'attempts': 5,
            'time_taken': 1.0,
            'found': False,
            'reason': 'stopped',
        })
        self.assertIn('was stopped', recommendation)
        self.assertNotIn('successfully resisted', recommendation)

    def test_exhausted_search_recommendation_is_limited_to_candidate_list(self):
        from ai.recommendation_engine import generate_ai_recommendation

        ratings = {
            'security_strength': 5.0,
            'memorability': 5.0,
            'randomness': 5.0,
            'pattern_safety': 5.0,
            'typing_usability': 5.0,
        }
        recommendation = generate_ai_recommendation('A_long_test_password_2026!', ratings, {
            'method': 'Dictionary',
            'attempts': 20,
            'time_taken': 2.0,
            'found': False,
            'reason': 'exhausted',
        })
        self.assertIn('exhausted its configured candidate list', recommendation)
        self.assertNotIn('successfully resisted', recommendation)

    def test_limit_recommendation_does_not_claim_password_resistance(self):
        from ai.recommendation_engine import generate_ai_recommendation

        ratings = {
            'security_strength': 5.0,
            'memorability': 5.0,
            'randomness': 5.0,
            'pattern_safety': 5.0,
            'typing_usability': 5.0,
        }
        recommendation = generate_ai_recommendation('A_long_test_password_2026!', ratings, {
            'method': 'Brute Force',
            'attempts': 5,
            'time_taken': 1.0,
            'found': False,
            'reason': 'limit_reached',
        })
        self.assertIn('does not prove the password would resist', recommendation)
        self.assertNotIn('successfully resisted', recommendation)


if __name__ == '__main__':
    unittest.main()
