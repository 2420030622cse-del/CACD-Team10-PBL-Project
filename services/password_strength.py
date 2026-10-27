from __future__ import annotations

from zxcvbn import zxcvbn

STRENGTH_LABELS = {
    0: 'Very Weak',
    1: 'Weak',
    2: 'Fair',
    3: 'Strong',
    4: 'Very Strong',
}


def analyze_password_strength(password: str | None):
    """Return a zxcvbn-based password-strength summary."""
    candidate = (password or '').strip()
    if not candidate:
        return {
            'score': 0,
            'label': f"Strength: {STRENGTH_LABELS[0]}",
            'strength_label': STRENGTH_LABELS[0],
            'guesses': 0,
            'crack_time': 'N/A',
            'offline_crack_time': 'N/A',
            'warning': 'Password required for analysis.',
            'suggestions': [],
            'feedback': {'warning': 'Password required for analysis.', 'suggestions': []},
            'pattern': 'No pattern detected',
            'patterns': [],
        }

    result = zxcvbn(candidate)
    score = int(result.get('score', 0))
    feedback = result.get('feedback', {})
    warning = feedback.get('warning') or 'No obvious pattern detected.'
    suggestions = feedback.get('suggestions') or []

    times_display = result.get('crack_times_display', {})
    guesses = int(result.get('guesses', 0))
    crack_time = times_display.get(
        'offline_fast_hashing_1e10_per_second',
        times_display.get('offline_fast_hashing_1e2_per_second', 'less than a second'),
    )
    offline_crack_time = times_display.get('offline_slow_hashing_1e4_per_second', 'less than a second')

    label = f"Strength: {STRENGTH_LABELS.get(score, STRENGTH_LABELS[0])}"

    return {
        'score': score,
        'label': label,
        'strength_label': STRENGTH_LABELS.get(score, STRENGTH_LABELS[0]),
        'guesses': guesses,
        'crack_time': crack_time,
        'offline_crack_time': offline_crack_time,
        'warning': warning,
        'suggestions': suggestions,
        'feedback': feedback,
        'pattern': warning,
        'patterns': result.get('sequence', []) if isinstance(result.get('sequence'), list) else [],
    }
