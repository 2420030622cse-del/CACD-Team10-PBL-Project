from flask import Flask, render_template, request, jsonify, session
import os
import secrets
import time
import math

# Import simulator modules
from simulator.password_validator import validate_password
from simulator.password_analyzer import analyze_password_preview
from simulator.statistics import calculate_search_space, format_number, calculate_time_estimate, get_length_growth_data
from simulator.brute_force import generate_brute_force_batch, get_charset
from simulator.dictionary import generate_dictionary_batch
from simulator.rule_based import DEFAULT_RULES, generate_rule_based_batch_details
from simulator.hybrid import generate_hybrid_batch

# Import security analysis services
from services.password_strength import analyze_password_strength
from services.hibp import check_pwned_password

# Import AI modules
from ai.password_model import load_models, predict_dimensions
from ai.recommendation_engine import identify_aspects, generate_ai_recommendation

# Import Database
from database.database import init_db, save_simulation, get_history, get_statistics

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
APP_ENV = os.environ.get('APP_ENV', 'development').lower()
if APP_ENV == 'production' and not os.environ.get('SECRET_KEY'):
    raise RuntimeError('SECRET_KEY must be set when APP_ENV=production.')
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=APP_ENV == 'production',
    MAX_CONTENT_LENGTH=16 * 1024,
)
PASSWORD_STORE = {}
VALID_PASSWORD_TYPES = {'PIN', 'TEXT', 'MIX'}
VALID_ATTACK_METHODS = {'brute_force', 'dictionary', 'rule_based', 'hybrid', 'password_safety'}
SIMULATION_METHODS = VALID_ATTACK_METHODS - {'password_safety'}


def store_test_password(password: str):
    expiry = time.time() - 1800
    for existing_token, (_, created_at) in list(PASSWORD_STORE.items()):
        if created_at < expiry:
            PASSWORD_STORE.pop(existing_token, None)
    while len(PASSWORD_STORE) >= 1000:
        oldest_token = min(PASSWORD_STORE, key=lambda key: PASSWORD_STORE[key][1])
        PASSWORD_STORE.pop(oldest_token, None)
    token = secrets.token_urlsafe(16)
    PASSWORD_STORE[token] = (password, time.time())
    session['test_password_token'] = token
    return token


def get_test_password():
    token = session.get('test_password_token')
    if token and token in PASSWORD_STORE:
        password, created_at = PASSWORD_STORE[token]
        if time.time() - created_at < 1800:
            return password
        PASSWORD_STORE.pop(token, None)
    legacy_password = session.get('test_password', '')
    if legacy_password:
        store_test_password(legacy_password)
        session.pop('test_password', None)
        return legacy_password
    return ''


def clear_test_password():
    token = session.get('test_password_token')
    if token:
        PASSWORD_STORE.pop(token, None)
    session.pop('test_password_token', None)
    session.pop('test_password', None)


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def valid_password_type(value):
    return value if isinstance(value, str) and value in VALID_PASSWORD_TYPES else None


@app.after_request
def add_api_cors_headers(response):
    origin = request.headers.get('Origin')
    allowed_origins = {
        value.strip()
        for value in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
        if value.strip()
    }
    if origin and (origin in allowed_origins or '*' in allowed_origins):
        response.headers['Access-Control-Allow-Origin'] = '*' if '*' in allowed_origins else origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Vary'] = 'Origin'
    return response


# Routes to render templates
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/attacks')
def attacks():
    return render_template('attacks.html')

@app.route('/configure')
def configure():
    method = request.args.get('method', 'brute_force')
    if method not in VALID_ATTACK_METHODS:
        method = 'brute_force'
    return render_template('configure.html', method=method)

@app.route('/simulation')
def simulation():
    # Retrieve configuration from query params
    method = request.args.get('method', 'brute_force')
    ptype = valid_password_type(request.args.get('type', 'PIN'))
    if method not in SIMULATION_METHODS or not ptype:
        return render_template('configure.html', error='Invalid simulation configuration.', method='brute_force')
    password = get_test_password()
    
    # Calculate limits from config
    max_attempts = request.args.get('max_attempts', 0 if method == 'brute_force' else 1000000, type=int)
    max_time = request.args.get('max_time', 0 if method == 'brute_force' else 60, type=int)
    speed = request.args.get('speed', 120, type=int)
    max_attempts = max(0, min(max_attempts, 10_000_000))
    max_time = max(0, min(max_time, 300))
    speed = max(1, min(speed, 500))
    rule_ids = request.args.get('rules', '')
    rule_ids = [rule for rule in rule_ids.split(',') if rule in DEFAULT_RULES.get(ptype, [])]
    max_rules = max(1, min(request.args.get('max_rules', 2, type=int), 4))
    
    if not password:
        return render_template('configure.html', error="Password not found. Please re-enter.", method=method)
        
    length = len(password)
    search_space, _, _ = calculate_search_space(ptype, length)
    formatted_space = format_number(search_space)
    worst_time = calculate_time_estimate(search_space, speed)
    
    return render_template('simulation.html', 
                           method=method, 
                           ptype=ptype, 
                           search_space=search_space,
                           formatted_space=formatted_space,
                           worst_time=worst_time,
                           max_attempts=max_attempts,
                           max_time=max_time,
                           speed=speed,
                           rule_ids=rule_ids if 'rules' in request.args else DEFAULT_RULES.get(ptype, []),
                           max_rules=max_rules)

@app.route('/report')
def report():
    password = get_test_password()
    if not password:
        return render_template('index.html')
        
    params = {
        'method': request.args.get('method', 'brute_force'),
        'type': request.args.get('type', 'PIN'),
        'attempts': max(0, min(request.args.get('attempts', 0, type=int), 10_000_000)),
        'time_taken': max(0.0, min(request.args.get('time_taken', 0.0, type=float), 86_400.0)),
        'speed': max(0.0, min(request.args.get('speed', 120.0, type=float), 1_000_000_000.0)),
        'found': request.args.get('found', 'true').lower() == 'true',
        'reason': request.args.get('reason', ''),
    }
    if params['reason'] not in {'', 'cracked', 'limit_reached', 'exhausted', 'stopped'}:
        params['reason'] = ''
    params['reason'] = params['reason'] or ('cracked' if params['found'] else 'limit_reached')
    if params['found']:
        params['reason'] = 'cracked'
    elif params['reason'] == 'cracked':
        params['reason'] = 'limit_reached'
    if (not valid_password_type(params['type'])
            or params['method'] not in SIMULATION_METHODS
            or params['attempts'] < 0
            or params['time_taken'] < 0
            or params['speed'] < 0):
        return render_template('configure.html', error='Invalid password type.', method=params['method'])
    report_data = create_report_data(password, params)
    ratings = report_data['ratings']
    
    # Save simulation history (never save plain text password).
    save_simulation(
        password_type=params['type'],
        attack_method=params['method'],
        attempts=params['attempts'],
        time_taken=params['time_taken'],
        average_speed=params['speed'],
        result='cracked' if params['found'] else params['reason'],
        ai_rating=ratings['overall_rating']
    )
    
    return render_template('report.html',
                           password_len=len(password), method=params['method'], ptype=params['type'],
                           attempts=params['attempts'], time_taken=params['time_taken'], speed=params['speed'],
                           reason=params['reason'],
                           found=params['found'], ratings=ratings, aspects=report_data['aspects'],
                           recommendation=report_data['recommendation'],
                           formatted_space=report_data['formatted_space'])


def create_report_data(password, params):
    ratings = predict_dimensions(password)
    aspects = identify_aspects(ratings)
    attack_results = {
        'method': params['method'].replace('_', ' ').title(),
        'attempts': params['attempts'],
        'time_taken': params['time_taken'],
        'average_speed': params['speed'],
        'found': params['found'],
        'reason': params.get('reason', 'cracked' if params['found'] else 'limit_reached'),
    }
    search_space, _, chars = calculate_search_space(params['type'], len(password))
    if params['method'] == 'brute_force' and params['type'] == 'PIN':
        search_space = chars ** len(password)
    return {
        'ratings': ratings,
        'aspects': aspects,
        'recommendation': generate_ai_recommendation(password, ratings, attack_results),
        'formatted_space': format_number(search_space),
    }


@app.route('/api/report', methods=['POST'])
def api_report():
    data = json_body()
    password = data.get('password', '')
    ptype = valid_password_type(data.get('type', 'PIN'))
    method = data.get('method', 'brute_force')
    if not isinstance(password, str) or not password:
        return jsonify({'error': 'A test password is required to generate the report.'}), 400
    if len(password) > 128:
        return jsonify({'error': 'The test password is too long.'}), 400
    if not ptype or method not in {'brute_force', 'dictionary', 'rule_based', 'hybrid'}:
        return jsonify({'error': 'Invalid report configuration.'}), 400
    try:
        params = {
            'method': method,
            'type': ptype,
            'attempts': max(0, min(int(data.get('attempts', 0)), 10_000_000)),
            'time_taken': max(0.0, min(float(data.get('time_taken', 0)), 86_400.0)),
            'speed': max(0.0, min(float(data.get('speed', 0)), 1_000_000_000.0)),
            'found': data.get('found') is True or str(data.get('found', '')).lower() == 'true',
            'reason': data.get('reason', ''),
        }
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid report metrics.'}), 400
    if not math.isfinite(params['time_taken']) or not math.isfinite(params['speed']):
        return jsonify({'error': 'Invalid report metrics.'}), 400
    if params['reason'] not in {'', 'cracked', 'limit_reached', 'exhausted', 'stopped'}:
        return jsonify({'error': 'Invalid report result.'}), 400
    params['reason'] = params['reason'] or ('cracked' if params['found'] else 'limit_reached')
    if (params['found'] and params['reason'] != 'cracked') or (not params['found'] and params['reason'] == 'cracked'):
        return jsonify({'error': 'Report result does not match the found status.'}), 400
    report_data = create_report_data(password, params)
    save_simulation(
        password_type=ptype,
        attack_method=method,
        attempts=params['attempts'],
        time_taken=params['time_taken'],
        average_speed=params['speed'],
        result='cracked' if params['found'] else params['reason'],
        ai_rating=report_data['ratings']['overall_rating'],
    )
    return jsonify(report_data)

# API Endpoints
@app.route('/api/validate', methods=['POST'])
def api_validate():
    data = json_body()
    password = data.get('password', '')
    ptype = valid_password_type(data.get('type', 'PIN')) or 'PIN'
    if not isinstance(password, str) or len(password) > 128:
        password = ''
    
    is_valid, reqs = validate_password(password, ptype)
    
    preview_data = None
    if is_valid:
        # Store only a session token and keep the plain-text value in an ephemeral in-memory store.
        origin = request.headers.get('Origin')
        backend_origin = f'{request.scheme}://{request.host}'
        if APP_ENV != 'production' and (not origin or origin == backend_origin):
            store_test_password(password)
        # Get preview features and metrics
        preview_data = analyze_password_preview(password)
        
    return jsonify({
        'is_valid': is_valid,
        'requirements': reqs,
        'analysis': preview_data
    })


@app.route('/api/security-analysis', methods=['POST'])
def api_security_analysis():
    data = json_body()
    password = data.get('password', '')
    if not isinstance(password, str) or len(password) > 128:
        password = ''
    if not password:
        return jsonify({
            'strength': analyze_password_strength(''),
            'hibp': {
                'compromised': False,
                'count': 0,
                'status': 'Unable to determine',
                'message': 'Enter a valid password to run security analysis.'
            }
        })

    strength_result = analyze_password_strength(password)
    hibp_result = check_pwned_password(password)
    return jsonify({
        'strength': strength_result,
        'hibp': hibp_result,
        'privacy_note': 'The configured backend analyzes your password. HIBP uses k-anonymity, so only the first 5 characters of its SHA-1 hash are transmitted.'
    })


@app.route('/api/reset-password', methods=['POST'])
def api_reset_password():
    clear_test_password()
    return jsonify({'status': 'cleared'})


@app.route('/api/simulate-step', methods=['POST'])
def api_simulate_step():
    data = json_body()
    method = data.get('method', 'brute_force')
    ptype = valid_password_type(data.get('type', 'PIN'))
    password = data.get('password') or get_test_password()
    state = data.get('state', {})
    if not isinstance(state, dict):
        return jsonify({'error': 'Invalid simulation state.'}), 400
    numeric_state_keys = {
        'index', 'length', 'max_length', 'attempts', 'index1', 'index2', 'mode',
        'word_index', 'variant_index', 'base_index', 'variation_index',
    }
    for key, value in state.items():
        if key in numeric_state_keys:
            if type(value) is not int or value < 0 or value > 10_000_000:
                return jsonify({'error': 'Invalid simulation state.'}), 400
        elif key == 'exhausted':
            if not isinstance(value, bool):
                return jsonify({'error': 'Invalid simulation state.'}), 400
        elif key == 'run_id':
            if not isinstance(value, str) or len(value) > 64:
                return jsonify({'error': 'Invalid simulation state.'}), 400
        else:
            return jsonify({'error': 'Invalid simulation state.'}), 400
    try:
        batch_size = max(1, min(int(data.get('batch_size', 500)), 500))
        max_rules = max(1, min(int(data.get('max_rules', 2)), 4))
        elapsed_time = max(0.0, min(float(data.get('elapsed_time', 0)), 86_400.0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid simulation limits.'}), 400
    if not math.isfinite(elapsed_time):
        return jsonify({'error': 'Invalid simulation limits.'}), 400
    charset = data.get('charset')
    if charset is not None and (not isinstance(charset, str) or len(charset) > 128):
        return jsonify({'error': 'Invalid character set.'}), 400
    enabled_rules = data.get('rules')
    if not isinstance(enabled_rules, list):
        enabled_rules = None
    else:
        if len(enabled_rules) > 32 or not all(isinstance(rule, str) for rule in enabled_rules):
            return jsonify({'error': 'Invalid rule selection.'}), 400
        enabled_rules = [rule for rule in enabled_rules if rule in DEFAULT_RULES.get(ptype, [])]
    if not ptype or not isinstance(password, str) or not password or len(password) > 128:
        return jsonify({'error': 'No test password configured in session'}), 400
        
    # Dispatch to correct generator
    attempts_before = state.get('attempts', state.get('index', 0))
    if method == 'brute_force':
        guesses, found, next_state, count = generate_brute_force_batch(ptype, password, state, batch_size, charset)
    elif method == 'dictionary':
        guesses, found, next_state, count = generate_dictionary_batch(ptype, password, state, batch_size)
    elif method == 'rule_based':
        from simulator.rule_based import generate_rule_based_batch_details
        started_at = time.perf_counter()
        records, found, next_state, count, matched_record = generate_rule_based_batch_details(
            ptype, password, state, batch_size, enabled_rules, max_rules
        )
        sampled_records = records
        if len(records) > 15:
            sampled_records = [records[round(index * (len(records) - 1) / 14)] for index in range(15)]
        guesses = [record['candidate'] for record in sampled_records]
    elif method == 'password_safety':
        return jsonify({
            'error': 'Password Safety Analysis uses the integrated API services instead of a simulated attack.',
            'uses_api': True,
            'api_sources': ['local validation', 'AI preview', 'zxcvbn strength', 'HIBP breach lookup']
        }), 400
    elif method == 'hybrid':
        guesses, found, next_state, count = generate_hybrid_batch(ptype, password, state, batch_size)
    else:
        return jsonify({'error': 'Invalid attack method'}), 400
        
    response = {
        'guesses': guesses,
        'found': found,
        'state': next_state,
        'count': count,
        'exhausted': next_state.get('exhausted', False),
        'result': {
            'candidate': password,
            'attempts': next_state.get('attempts', count),
            'length': len(password),
        } if found else None,
    }
    if method == 'rule_based':
        response['guess_attempts'] = [record['attempt'] for record in sampled_records]
    else:
        sample_offsets = (
            [round(index * (count - 1) / 14) for index in range(15)]
            if count > 15 else list(range(len(guesses)))
        )
        response['guess_attempts'] = [
            attempts_before + offset + 1 for offset in sample_offsets
        ]
    if method == 'rule_based':
        response['candidate_details'] = sampled_records
        response['result'] = {
            'method': 'Rule Based',
            'passwordType': {'PIN': 'PIN', 'TEXT': 'Text', 'MIX': 'Mixed'}.get(ptype, ptype),
            'found': found,
            'matchedCandidate': matched_record['candidate'] if matched_record else None,
            'attempts': next_state.get('attempts', count),
            'baseWord': matched_record['base_word'] if matched_record else None,
            'rulesUsed': matched_record['rules'] if matched_record else [],
            'elapsedTime': round(max(0.0, elapsed_time if 'elapsed_time' in data else time.perf_counter() - started_at), 6),
        } if found else None
    return jsonify(response)

@app.route('/api/compare-methods', methods=['GET', 'POST'])
def api_compare_methods():
    data = json_body() if request.method == 'POST' else {}
    password = data.get('password') or get_test_password()
    ptype = valid_password_type(data.get('type') or request.args.get('type', 'PIN'))

    if not ptype or not isinstance(password, str) or not password or len(password) > 128:
        return jsonify({'error': 'No password in session'}), 400
        
    # Calculate estimations for search spaces and how fast each method would crack it
    # 1. Dictionary search space size
    from simulator.dictionary import get_dictionary_list
    dict_list = get_dictionary_list(ptype)
    dict_space = len(dict_list)
    
    # 2. Count the exact unique candidates produced by the default rule search.
    rule_space = 0
    rule_attempts = None
    rule_state = {}
    while True:
        records, _, rule_state, count, _ = generate_rule_based_batch_details(
            ptype, '', rule_state, batch_size=5000
        )
        if rule_attempts is None:
            match = next((record for record in records if record['candidate'] == password), None)
            if match:
                rule_attempts = match['attempt']
        rule_space += count
        if rule_state.get('exhausted') or not count:
            break
    rule_found = rule_attempts is not None
    if not rule_found:
        rule_attempts = rule_space

    # 3. Measure the actual hybrid candidate list and the target's position.
    hybrid_space = 0
    hybrid_attempts = None
    hybrid_state = {}
    while True:
        _, found, hybrid_state, count = generate_hybrid_batch(
            ptype, password, hybrid_state, batch_size=5000
        )
        if found and hybrid_attempts is None:
            hybrid_attempts = hybrid_space + count
        hybrid_space += count
        if hybrid_state.get('exhausted') or not count:
            break
    hybrid_found = hybrid_attempts is not None
    if not hybrid_found:
        hybrid_attempts = hybrid_space

    # 4. Brute force size
    brute_space, _, _ = calculate_search_space(ptype, len(password))
    dict_found = password in dict_list
    dict_attempts = dict_list.index(password) + 1 if dict_found else dict_space

    # Brute force uses fixed-length base-N enumeration, so the exact rank is calculable.
    charset = get_charset(ptype)
    if all(character in charset for character in password):
        brute_index = 0
        for character in password:
            brute_index = brute_index * len(charset) + charset.index(character)
        brute_attempts = brute_index + 1
        brute_found = True
    else:
        brute_attempts = brute_space
        brute_found = False
        
    return jsonify({
        'methods': ['Brute Force', 'Dictionary', 'Rule-Based', 'Hybrid'],
        'search_spaces': [brute_space, dict_space, rule_space, hybrid_space],
        'search_spaces_formatted': [format_number(brute_space), format_number(dict_space), format_number(rule_space), format_number(hybrid_space)],
        'attempts_needed': [brute_attempts, dict_attempts, rule_attempts, hybrid_attempts],
        'found': [brute_found, dict_found, rule_found, hybrid_found]
    })

@app.route('/api/length-growth', methods=['GET'])
def api_length_growth():
    ptype = request.args.get('type', 'PIN')
    data = get_length_growth_data(ptype, 6)
    return jsonify(data)

@app.route('/api/history', methods=['GET'])
def api_history():
    history = get_history(15)
    return jsonify(history)

@app.route('/api/stats', methods=['GET'])
def api_stats():
    stats = get_statistics()
    return jsonify(stats)

if __name__ == '__main__':
    # Initialize DB
    init_db()
    
    # Train AI Models on startup if necessary
    load_models()
    
    app.run(debug=APP_ENV != 'production', port=int(os.environ.get('PORT', '5000')))
