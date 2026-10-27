import sqlite3
import os

DB_PATH = os.environ.get(
    'DATABASE_PATH',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db'),
)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the simulation_history table if it doesn't exist."""
    # Ensure directory exists
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = get_db_connection()
    try:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS simulation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                password_type TEXT NOT NULL,
                attack_method TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                time_taken REAL NOT NULL,
                average_speed REAL NOT NULL,
                result TEXT NOT NULL,
                ai_rating REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def save_simulation(password_type, attack_method, attempts, time_taken, average_speed, result, ai_rating):
    """Saves a completed simulation run to the database."""
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO simulation_history 
            (password_type, attack_method, attempts, time_taken, average_speed, result, ai_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (password_type, attack_method, attempts, time_taken, average_speed, result, ai_rating))
        conn.commit()
    finally:
        conn.close()

def get_history(limit=10):
    """Retrieves the recent simulation records."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, password_type, attack_method, attempts, time_taken, average_speed, result, ai_rating, timestamp
            FROM simulation_history
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_statistics():
    """Calculates general statistics from all simulation history."""
    conn = get_db_connection()
    stats = {
        'total_simulations': 0,
        'success_count': 0,
        'average_time': 0.0,
        'average_attempts': 0.0,
        'average_rating': 0.0,
        'by_method': {},
        'by_type': {}
    }
    try:
        cursor = conn.cursor()
        
        # General metrics
        cursor.execute('SELECT COUNT(*), AVG(time_taken), AVG(attempts), AVG(ai_rating) FROM simulation_history')
        row = cursor.fetchone()
        if row and row[0] > 0:
            stats['total_simulations'] = row[0]
            stats['average_time'] = round(row[1], 2) if row[1] is not None else 0.0
            stats['average_attempts'] = round(row[2], 2) if row[2] is not None else 0.0
            stats['average_rating'] = round(row[3], 2) if row[3] is not None else 0.0
            
        # Success count
        cursor.execute("SELECT COUNT(*) FROM simulation_history WHERE result = 'cracked'")
        row_success = cursor.fetchone()
        if row_success:
            stats['success_count'] = row_success[0]
            
        # Group by attack method
        cursor.execute('SELECT attack_method, COUNT(*) FROM simulation_history GROUP BY attack_method')
        for method, count in cursor.fetchall():
            stats['by_method'][method] = count
            
        # Group by password type
        cursor.execute('SELECT password_type, COUNT(*) FROM simulation_history GROUP BY password_type')
        for ptype, count in cursor.fetchall():
            stats['by_type'][ptype] = count
            
    finally:
        conn.close()
    return stats
