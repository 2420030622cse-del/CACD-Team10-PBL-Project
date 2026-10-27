import re
from ai.feature_extractor import extract_features

DIMENSION_METRICS = {
    'security_strength': ('🛡️ SECURITY STRENGTH', {
        'high': "The password is exceptionally resilient to systematic guessing and dictionary matching.",
        'med': "The password provides basic protection, but remains vulnerable to targeted dictionary or rule-based attacks.",
        'low': "The password offers almost no resistance; automated attack scripts can guess it almost instantly."
    }),
    'memorability': ('🧠 MEMORABILITY', {
        'high': "The structure relies on common concepts or familiar words, making it easy for a human to remember.",
        'med': "It combines some readable words and numbers, meaning it can be memorized with moderate effort.",
        'low': "The random arrangement of characters makes it extremely difficult to recall without a password manager."
    }),
    'randomness': ('🎲 RANDOMNESS', {
        'high': "The character arrangement shows high entropy and very little predictable structure.",
        'med': "Some segments of the password are randomized, but other parts follow predictable schemas.",
        'low': "The character sequences are highly predictable or repeat frequently, reducing uncertainty."
    }),
    'pattern_safety': ('🧩 PATTERN SAFETY', {
        'high': "No recognizable sequences, keyboard walks, or sequential numerical digits were detected.",
        'med': "Contains minor pattern sequences (like small runs of consecutive letters or numbers).",
        'low': "Highly vulnerable due to common patterns (e.g., sequential digits, alphabetical runs, or popular words)."
    }),
    'typing_usability': ('⌨️ TYPING USABILITY', {
        'high': "Features standard layout distributions that are easy to type quickly and accurately on mobile or physical keyboards.",
        'med': "Requires moving across different keyboard layouts, which might lead to occasional typing mistakes.",
        'low': "Requires frequent, complex shifting between special characters, numbers, and cases, making it highly prone to typos."
    })
}

def identify_aspects(ratings):
    """
    Identifies the strongest and weakest aspects from the ratings.
    """
    dims = ['security_strength', 'memorability', 'randomness', 'pattern_safety', 'typing_usability']
    
    # Exclude overall_rating
    scores = {d: ratings[d] for d in dims}
    
    strongest_dim = max(scores, key=scores.get)
    weakest_dim = min(scores, key=scores.get)
    
    # Handle edge case where strongest and weakest are same
    if strongest_dim == weakest_dim:
        # Pick different ones by default
        weakest_dim = 'memorability' if strongest_dim == 'security_strength' else 'security_strength'
        
    def get_desc(dim, score_val, is_strongest):
        title, descs = DIMENSION_METRICS[dim]
        level = 'high' if score_val >= 7.0 else ('med' if score_val >= 4.0 else 'low')
        
        # Customize explanation based on context
        if is_strongest:
            return f"With a score of {score_val}/10, this is your password's core defense. {descs[level]}"
        else:
            return f"Scoring just {score_val}/10, this is the main bottleneck. {descs[level]}"

    return {
        'strongest': {
            'key': strongest_dim,
            'name': DIMENSION_METRICS[strongest_dim][0],
            'score': ratings[strongest_dim],
            'description': get_desc(strongest_dim, ratings[strongest_dim], True)
        },
        'weakest': {
            'key': weakest_dim,
            'name': DIMENSION_METRICS[weakest_dim][0],
            'score': ratings[weakest_dim],
            'description': get_desc(weakest_dim, ratings[weakest_dim], False)
        }
    }

def generate_ai_recommendation(password, ratings, attack_results):
    """
    Generates a natural-language recommendation paragraph based on features, ML scores, and simulator statistics.
    """
    feats = extract_features(password)
    
    # Extract variables
    method = attack_results.get('method', 'Unknown')
    attempts = attack_results.get('attempts', 0)
    time_taken = attack_results.get('time_taken', 0.0)
    found = attack_results.get('found', False)
    
    rec_sentences = []
    
    # 1. Analyze the simulation results
    if found:
        speed_str = f"{attack_results.get('average_speed', 0.0):,.0f}"
        rec_sentences.append(
            f"During the live test, the {method} simulation successfully cracked this password in "
            f"{time_taken:.2f} seconds, requiring only {attempts:,} attempts. This demonstrates "
            f"how vulnerable simple password configurations are to automation."
        )
    elif attack_results.get('reason') == 'stopped':
        rec_sentences.append(
            f"The {method} simulation was stopped after {attempts:,} attempts over {time_taken:.2f} seconds, "
            "before the test password was found. This run does not establish that the password resisted the full search."
        )
    elif attack_results.get('reason') == 'exhausted':
        rec_sentences.append(
            f"The {method} simulation exhausted its configured candidate list after {attempts:,} attempts over "
            f"{time_taken:.2f} seconds without finding the test password. This only describes the selected list, "
            "not every possible password."
        )
    else:
        rec_sentences.append(
            f"The password successfully resisted the {method} simulation, which reached its configuration limit "
            f"of {attempts:,} attempts over {time_taken:.2f} seconds without discovering the password. "
            f"This shows a strong initial defense against the tested attack parameters."
        )
        
    # 2. Add structural analysis sentences
    if feats['is_dictionary_word']:
        rec_sentences.append(
            "The password is heavily compromised because it incorporates a common English word or basic password pattern. "
            "Dictionary-based attacks are optimized to exploit this exact weakness, bypassing millions of other combinations."
        )
    elif feats['keyboard_pattern_count'] > 0:
        rec_sentences.append(
            "Our feature extraction detected predictable character sequences or keyboard walking patterns (e.g., '1234' or 'qwerty'). "
            "Attackers construct rule-based dictionaries specifically to test these common muscle-memory sequences."
        )
        
    if feats['consecutive_char_max'] >= 3:
        rec_sentences.append(
            "It also contains repeated consecutive characters, which reduces its overall complexity and makes it easier to crack."
        )

    # 3. Add Trade-off analysis
    sec_score = ratings['security_strength']
    mem_score = ratings['memorability']
    usab_score = ratings['typing_usability']
    
    if sec_score >= 8.0 and mem_score <= 3.0:
        rec_sentences.append(
            "This is a mathematically secure password. However, its high entropy means a human will find it "
            "extremely difficult to memorize or type correctly, particularly on mobile devices. "
            "We recommend saving this password in a secure password manager rather than trying to memorize it."
        )
    elif sec_score <= 4.0 and mem_score >= 7.0:
        rec_sentences.append(
            "While this password is highly memorable, it is too weak for modern security standards. "
            "An attacker utilizing standard brute-force or rule-based permutations can breach this quickly. "
            "Consider converting it to a passphrase (e.g., combining 4 random, unrelated words) to increase length "
            "without sacrificing memorability."
        )
    else:
        rec_sentences.append(
            "The password represents a moderate compromise between safety and usability. However, to stay secure "
            "against modern GPU-accelerated cracking setups, passwords should ideally aim for a security strength above 8.0."
        )
        
    # 4. Actionable tips
    tips = []
    if feats['length'] < 12:
        tips.append("increase its length to at least 12-16 characters (length is the single most effective defense)")
    if feats['uppercase_count'] == 0:
        tips.append("introduce uppercase letters")
    if feats['number_count'] < 3:
        tips.append("add more digits dispersed throughout the string (not just at the very end)")
    if feats['symbol_count'] == 0:
        tips.append("include special symbols like '@', '#', or '!'")
        
    if tips:
        rec_sentences.append(
            f"To strengthen this password, you should " + ", ".join(tips[:-1]) + f", and {tips[-1]}." if len(tips) > 1 else f"To strengthen this password, you should {tips[0]}."
        )
        
    return " ".join(rec_sentences)
