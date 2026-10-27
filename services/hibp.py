from __future__ import annotations

import hashlib
import urllib.error
import urllib.request

HIBP_URL = 'https://api.pwnedpasswords.com/range/'
USER_AGENT = 'CyberForcePasswordChecker/1.0'


def _sha1_hex(password: str) -> str:
    return hashlib.sha1(password.encode('utf-8')).hexdigest().upper()


def check_pwned_password(password: str | None):
    """Check whether a password appears in the HIBP pwned passwords dataset using k-anonymity."""
    candidate = (password or '').strip()
    if not candidate:
        return {
            'compromised': False,
            'count': 0,
            'status': 'Unavailable',
            'message': 'No password supplied for HIBP analysis.',
        }

    sha1_hash = _sha1_hex(candidate)
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]

    request = urllib.request.Request(
        f'{HIBP_URL}{prefix}',
        headers={'User-Agent': USER_AGENT, 'Add-Padding': 'true'},
    )

    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            body = response.read().decode('utf-8', errors='replace')
            for line in body.splitlines():
                if not line:
                    continue
                parts = line.split(':')
                if len(parts) < 2:
                    continue
                candidate_suffix = parts[0].strip()
                if candidate_suffix == suffix:
                    count = int(parts[1].strip())
                    return {
                        'compromised': True,
                        'count': count,
                        'status': 'FOUND',
                        'message': 'Password found in known breach datasets.',
                    }
            return {
                'compromised': False,
                'count': 0,
                'status': 'NOT FOUND',
                'message': 'Password not found in pwned password datasets.',
            }
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return {
                'compromised': False,
                'count': 0,
                'status': 'Unable to determine',
                'message': 'HIBP rate limit reached. Your password was not sent elsewhere.',
            }
        return {
            'compromised': False,
            'count': 0,
            'status': 'Unable to determine',
            'message': f'HIBP service responded with HTTP {exc.code}. Your password was not sent elsewhere.',
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {
            'compromised': False,
            'count': 0,
            'status': 'Unable to determine',
            'message': 'The HIBP service could not be reached. Your password was not sent elsewhere.',
        }
