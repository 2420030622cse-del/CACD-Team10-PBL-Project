from ai.password_model import predict_dimensions
from ai.feature_extractor import extract_features

def get_qualitative_label(score):
    """Converts a 0-10 score to a qualitative labels."""
    if score >= 8.0:
        return "Very High" if score >= 9.0 else "High"
    elif score >= 5.0:
        return "Moderate"
    elif score >= 3.0:
        return "Low"
    else:
        return "Very Low"

def analyze_password_preview(password):
    """
    Performs feature analysis and calls ML model to predict rating scores,
    then formats it into a qualitative preview for the UI.
    """
    ratings = predict_dimensions(password)
    feats = extract_features(password)
    
    return {
        'features': feats,
        'preview': {
            'security_strength': get_qualitative_label(ratings['security_strength']),
            'memorability': get_qualitative_label(ratings['memorability']),
            'randomness': get_qualitative_label(ratings['randomness']),
            'pattern_safety': get_qualitative_label(ratings['pattern_safety']),
            'typing_usability': get_qualitative_label(ratings['typing_usability'])
        },
        'ratings': ratings
    }
