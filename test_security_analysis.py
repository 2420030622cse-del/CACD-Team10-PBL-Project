import hashlib
import unittest
from unittest.mock import patch

from services.password_strength import analyze_password_strength
from services.hibp import check_pwned_password


class SecurityAnalysisTests(unittest.TestCase):
    def test_password_strength_handles_empty_string(self):
        data = analyze_password_strength('')
        self.assertEqual(data['score'], 0)
        self.assertIn('Strength', data['label'])

    def test_password_strength_includes_feedback(self):
        data = analyze_password_strength('Password123')
        self.assertIn('score', data)
        self.assertIn('feedback', data)
        self.assertGreaterEqual(data['score'], 0)

    @patch('services.hibp.urllib.request.urlopen')
    def test_pwned_password_returns_match_for_compromised_password(self, mock_urlopen):
        candidate = 'password'
        sha1_hash = hashlib.sha1(candidate.encode('utf-8')).hexdigest().upper()
        suffix = sha1_hash[5:]

        mock_response = unittest.mock.Mock()
        mock_response.read.return_value = f'{suffix}:24\nABCDEF:99\n'.encode('utf-8')
        mock_response.__enter__ = lambda self: self
        mock_response.__exit__ = lambda *args: None
        mock_urlopen.return_value = mock_response

        result = check_pwned_password(candidate)
        self.assertTrue(result['compromised'])
        self.assertEqual(result['count'], 24)

    @patch('services.hibp.urllib.request.urlopen')
    def test_pwned_password_handles_network_errors(self, mock_urlopen):
        mock_urlopen.side_effect = OSError('network down')

        result = check_pwned_password('A_random_long_test_password_2026!')
        self.assertFalse(result['compromised'])
        self.assertEqual(result['count'], 0)
        self.assertIn('unable', result['status'].lower())


if __name__ == '__main__':
    unittest.main()
