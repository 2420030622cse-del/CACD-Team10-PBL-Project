import random
import string
from ai.feature_extractor import extract_features, get_feature_names

def generate_synthetic_passwords():
    """
    Generates a list of passwords and their calculated labels for 5 dimensions:
    - security_strength: 0 (Very Low) to 4 (Very High)
    - memorability: 0 (Very Low) to 4 (Very High)
    - randomness: 0 (Very Low) to 4 (Very High)
    - pattern_safety: 0 (Very Low) to 4 (Very High)
    - typing_usability: 0 (Very Low) to 4 (Very High)
    """
    data = []
    
    # 1. Simple numeric PINs (Low security, High memorability & usability)
    # Examples: '123456', '000000'
    for _ in range(100):
        # Sequential/repeated
        pw = ''.join(random.choice(['123456', '000000', '111111', '987654', '121212', '123123']))
        data.append((pw, 0, 4, 0, 0, 4))
        
    for _ in range(150):
        # Random PINs
        pw = ''.join(random.choices(string.digits, k=6))
        data.append((pw, 1, 3, 2, 3, 4))
        
    # 2. Simple dictionary words and variations
    words = ['password', 'admin', 'welcome', 'hello', 'security', 'qwerty', 'football', 'letmein', 'computer', 'monkey']
    for word in words:
        # Exact word
        data.append((word, 0, 4, 0, 0, 4))
        # Capitalized
        data.append((word.capitalize(), 0, 4, 0, 1, 4))
        # Word + simple number
        data.append((f"{word}123", 1, 4, 1, 1, 4))
        data.append((f"{word.capitalize()}1", 1, 4, 1, 2, 4))
        # Word + symbol
        data.append((f"{word}!", 1, 4, 1, 2, 3))
        # Word + number + symbol
        data.append((f"{word.capitalize()}123!", 2, 3, 2, 2, 3))

    # 3. Simple text (only letters, varying lengths)
    for _ in range(200):
        length = random.randint(8, 12)
        # Random simple letters
        pw = ''.join(random.choices(string.ascii_lowercase, k=length))
        data.append((pw, 1, 3, 2, 2, 3))
        
        # CamelCase text
        pw_cc = ''.join(random.choice(string.ascii_uppercase) + ''.join(random.choices(string.ascii_lowercase, k=3)) for _ in range(3))
        data.append((pw_cc, 2, 3, 2, 2, 3))

    # 4. Mix passwords (some structure)
    for _ in range(250):
        # Mixed but somewhat easy: Word + Year + Symbol
        word = random.choice(words).capitalize()
        year = str(random.randint(1970, 2026))
        sym = random.choice('!@#$%^&*')
        pw = f"{word}{year}{sym}"
        data.append((pw, 2, 3, 2, 2, 3))
        
        # Word + custom numbers + symbol (more complex)
        pw2 = f"{word}{''.join(random.choices(string.digits, k=4))}{sym}"
        data.append((pw2, 3, 2, 3, 3, 3))

    # 5. High-complexity random mix passwords (Very high security & randomness, low memorability)
    for _ in range(250):
        length = random.randint(10, 16)
        # Guarantees complex distribution
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + '!@#$%^&*'
        pw = ''.join(random.choices(chars, k=length))
        
        # Rate usability based on length and characters
        usability = 2 if length <= 12 else 1
        data.append((pw, 4, 0, 4, 4, usability))
        
    for _ in range(100):
        # Extremely long complex passwords
        length = random.randint(16, 20)
        chars = string.ascii_uppercase + string.ascii_lowercase + string.digits + '!@#$%^&*()_+'
        pw = ''.join(random.choices(chars, k=length))
        data.append((pw, 4, 0, 4, 4, 0))

    # Compile dataset
    dataset = []
    for pw, sec, mem, rand, pat, usab in data:
        features = extract_features(pw)
        dataset.append({
            'features': features,
            'labels': {
                'security_strength': sec,
                'memorability': mem,
                'randomness': rand,
                'pattern_safety': pat,
                'typing_usability': usab
            }
        })
        
    return dataset
