import math

def calculate_search_space(ptype, length):
    """
    Calculates the theoretical search space size.
    PIN: digits 0-9 (base 10)
    TEXT/MIX: printable ASCII characters without spaces (base 94)
    """
    if ptype == 'PIN':
        base = 10
        # PIN is always exactly 6 digits as per requirements
        chars = 10
        comb = base ** 6
    elif ptype == 'TEXT':
        base = 94
        chars = 94
        comb = base ** length
    elif ptype == 'MIX':
        base = 94
        chars = 94
        comb = base ** length
    else:
        base = 26
        chars = 26
        comb = base ** length
        
    return comb, base, chars

def format_number(val):
    """Converts a huge number into a readable short scale string."""
    if val < 1000:
        return str(val)
    elif val < 1000000:
        return f"{val/1000:.1f} Thousand"
    elif val < 1000000000:
        return f"{val/1000000:.2f} Million"
    elif val < 1000000000000:
        return f"{val/1000000000:.2f} Billion"
    elif val < 1000000000000000:
        return f"{val/1000000000000:.2f} Trillion"
    elif val < 1000000000000000000:
        return f"{val/1000000000000000:.2f} Quadrillion"
    else:
        return f"{val:.2e} Combinations"

def calculate_time_estimate(search_space, speed_per_sec):
    """Estimates the worst-case time in seconds to exhaust the search space."""
    if speed_per_sec <= 0:
        return "Infinite"
    seconds = search_space / speed_per_sec
    
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"{seconds/60:.1f} minutes"
    elif seconds < 86400:
        return f"{seconds/3600:.1f} hours"
    elif seconds < 31536000:
        return f"{seconds/86400:.1f} days"
    else:
        return f"{seconds/31536000:.1f} years"
        
def get_length_growth_data(ptype, base_length):
    """
    Generates data points for combinations growth from length 4 to 12.
    Used by Chart.js to plot exponential search space growth.
    """
    data = []
    # Determine base size
    if ptype == 'PIN':
        base = 10
    else:
        base = 94
        
    for l in range(4, 13):
        data.append({
            'length': l,
            'combinations': base ** l
        })
    return data
