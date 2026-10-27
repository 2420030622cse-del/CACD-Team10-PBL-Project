import os
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from ai.feature_extractor import extract_features, feature_dict_to_list
from ai.training_generator import generate_synthetic_passwords

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'password_models.pkl')

# Global variable to cache models
_models = None

def train_and_save_models():
    """Generates synthetic data, trains 5 RandomForestClassifiers, and pickles them."""
    print("Generating training dataset...")
    raw_data = generate_synthetic_passwords()
    
    # Prepare features
    X = []
    y_sec = []
    y_mem = []
    y_rand = []
    y_pat = []
    y_usab = []
    
    for item in raw_data:
        feat_list = feature_dict_to_list(item['features'])
        X.append(feat_list)
        y_sec.append(item['labels']['security_strength'])
        y_mem.append(item['labels']['memorability'])
        y_rand.append(item['labels']['randomness'])
        y_pat.append(item['labels']['pattern_safety'])
        y_usab.append(item['labels']['typing_usability'])
        
    X = np.array(X)
    
    models = {
        'security_strength': RandomForestClassifier(n_estimators=100, random_state=42),
        'memorability': RandomForestClassifier(n_estimators=100, random_state=42),
        'randomness': RandomForestClassifier(n_estimators=100, random_state=42),
        'pattern_safety': RandomForestClassifier(n_estimators=100, random_state=42),
        'typing_usability': RandomForestClassifier(n_estimators=100, random_state=42)
    }
    
    print("Training models...")
    models['security_strength'].fit(X, y_sec)
    models['memorability'].fit(X, y_mem)
    models['randomness'].fit(X, y_rand)
    models['pattern_safety'].fit(X, y_pat)
    models['typing_usability'].fit(X, y_usab)
    
    # Save to file
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(models, f)
    print(f"Models successfully saved to {MODEL_PATH}")
    return models

def load_models():
    """Loads models from disk, training them first if they don't exist."""
    global _models
    if _models is not None:
        return _models
        
    if not os.path.exists(MODEL_PATH):
        _models = train_and_save_models()
    else:
        try:
            with open(MODEL_PATH, 'rb') as f:
                _models = pickle.load(f)
            print("Loaded pre-trained models from disk.")
        except Exception as e:
            print(f"Error loading models: {e}. Retraining...")
            _models = train_and_save_models()
            
    return _models

def predict_dimensions(password):
    """
    Predicts the scores for the 5 security dimensions on a 0.0 - 10.0 scale.
    """
    models = load_models()
    feats = extract_features(password)
    feat_vector = np.array([feature_dict_to_list(feats)])
    
    ratings = {}
    for dim_name, clf in models.items():
        # Predict class probabilities
        probs = clf.predict_proba(feat_vector)[0]
        classes = clf.classes_
        
        # Calculate expected score on 0-4 scale: sum(prob_i * class_i)
        # then scale it to 0-10 by multiplying by 2.5
        expected_class_val = sum(p * c for p, c in zip(probs, classes))
        score = round(float(expected_class_val) * 2.5, 1)
        ratings[dim_name] = score
        
    # Calculate overall security score
    # Security strength and Pattern Safety are weighted heavier
    overall = (
        ratings['security_strength'] * 0.4 +
        ratings['pattern_safety'] * 0.2 +
        ratings['randomness'] * 0.2 +
        ratings['memorability'] * 0.1 +
        ratings['typing_usability'] * 0.1
    )
    ratings['overall_rating'] = round(float(overall), 1)
    return ratings
