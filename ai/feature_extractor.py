import math
import re

COMMON_DICT_WORDS = [
    'password', 'admin', 'welcome', 'hello', 'security', 'qwerty', 'computer', 'football', 'letmein', 'test',
    'pass', 'root', 'login', 'user', '123456', '12345678', 'monkey', 'dragon', 'secret', 'trust', 'oracle'
]

def calculate_entropy(password):
    """Calculates the Shannon entropy of a password string."""
    if not password:
        return 0.0
    
    char_counts = {}
    for char in password:
        char_counts[char] = char_counts.get(char, 0) + 1
        
    length = len(password)
    entropy = 0.0
    for count in char_counts.values():
        p = count / length
        entropy -= p * math.log2(p)
    return round(entropy, 3)

def check_sequential_patterns(password):
    """Counts sequential patterns (e.g., '1234', 'abcd', 'qwerty')."""
    password_lower = password.lower()
    sequences = [
        '1234567890', '0987654321',
        'abcdefghijklmnopqrstuvwxyz', 'zyxwvutsrqponmlkjihgfedcba',
        'qwertyuiop', 'asdfghjkl', 'zxcvbnm'
    ]
    
    count = 0
    # Check sequences of length 3 or more
    for seq in sequences:
        for i in range(len(seq) - 2):
            sub_seq = seq[i:i+3]
            if sub_seq in password_lower:
                count += 1
    return count

def get_max_consecutive(password):
    """Calculates the maximum consecutive identical characters."""
    if not password:
        return 0
    max_count = 1
    current_count = 1
    for i in range(1, len(password)):
        if password[i] == password[i-1]:
            current_count += 1
            if current_count > max_count:
                max_count = current_count
        else:
            current_count = 1
    return max_count

def extract_features(password):
    """
    Extracts a feature dictionary from a password.
    Returns:
        dict: Features extracted from the password.
    """
    if not password:
        return {
            'length': 0, 'entropy': 0.0, 'uppercase_count': 0, 'lowercase_count': 0,
            'number_count': 0, 'symbol_count': 0, 'unique_char_ratio': 0.0,
            'consecutive_char_max': 0, 'keyboard_pattern_count': 0, 'is_dictionary_word': 0
        }
        
    length = len(password)
    uppercase = sum(1 for c in password if c.isupper())
    lowercase = sum(1 for c in password if c.islower())
    numbers = sum(1 for c in password if c.isdigit())
    symbols = length - (uppercase + lowercase + numbers)
    
    unique_chars = len(set(password))
    unique_ratio = unique_chars / length if length > 0 else 0.0
    
    # Check dictionary words
    password_lower = password.lower()
    is_dict = 0
    for word in COMMON_DICT_WORDS:
        if word in password_lower:
            is_dict = 1
            break
            
    consecutive = get_max_consecutive(password)
    sequences = check_sequential_patterns(password)
    entropy = calculate_entropy(password)
    
    return {
        'length': length,
        'entropy': entropy,
        'uppercase_count': uppercase,
        'lowercase_count': lowercase,
        'number_count': numbers,
        'symbol_count': symbols,
        'unique_char_ratio': unique_ratio,
        'consecutive_char_max': consecutive,
        'keyboard_pattern_count': sequences,
        'is_dictionary_word': is_dict
    }

def get_feature_names():
    """Returns the ordered list of keys used in the feature extraction."""
    return [
        'length', 'entropy', 'uppercase_count', 'lowercase_count',
        'number_count', 'symbol_count', 'unique_char_ratio',
        'consecutive_char_max', 'keyboard_pattern_count', 'is_dictionary_word'
    ]

def feature_dict_to_list(feat_dict):
    """Converts a feature dict into an ordered list for ML models."""
    names = get_feature_names()
    return [feat_dict[name] for name in names]
