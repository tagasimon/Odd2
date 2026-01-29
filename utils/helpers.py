"""
Odd 2 - Helper Utilities
Common utility functions used throughout the application
"""
from datetime import datetime, timedelta
import pytz
from config import Config


def get_eat_timezone():
    """Get East Africa Time timezone object"""
    return pytz.timezone(Config.TIMEZONE)


def get_current_eat_time():
    """Get current time in East Africa Time"""
    return datetime.now(get_eat_timezone())


def get_next_update_time():
    """
    Calculate the next prediction update time (12 PM or 12 AM EAT)
    Returns: datetime object in EAT timezone
    """
    tz = get_eat_timezone()
    now = datetime.now(tz)
    
    # Check for today's update times
    for hour in Config.UPDATE_HOURS:
        update_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if update_time > now:
            return update_time
    
    # If all today's times have passed, return first time tomorrow
    tomorrow = now + timedelta(days=1)
    next_update = tomorrow.replace(hour=Config.UPDATE_HOURS[0], minute=0, second=0, microsecond=0)
    return next_update


def get_time_until_update():
    """
    Get time remaining until next update
    Returns: dict with hours, minutes, seconds
    """
    next_update = get_next_update_time()
    now = datetime.now(get_eat_timezone())
    
    delta = next_update - now
    total_seconds = int(delta.total_seconds())
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    return {
        'hours': hours,
        'minutes': minutes,
        'seconds': seconds,
        'total_seconds': total_seconds,
        'next_update': next_update.strftime('%I:%M %p')
    }


def format_odds(odds):
    """Format odds to 2 decimal places"""
    return f"{odds:.2f}"


def format_currency(amount, currency):
    """Format amount with currency symbol"""
    currency_symbols = {
        'UGX': 'UGX',
        'KES': 'KES',
        'TZS': 'TZS',
        'RWF': 'RWF',
        'BIF': 'BIF'
    }
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol} {amount:,.0f}"


def format_match_time(dt):
    """Format match datetime for display"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    tz = get_eat_timezone()
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    local_time = dt.astimezone(tz)
    return local_time.strftime('%d %b, %I:%M %p')


def generate_session_token():
    """Generate a unique session token"""
    import secrets
    return secrets.token_urlsafe(32)


def calculate_win_rate(predictions):
    """
    Calculate win rate from a list of predictions
    Returns: float (0.0 to 1.0) or None if no completed predictions
    """
    completed = [p for p in predictions if p.status in ['won', 'lost']]
    if not completed:
        return None
    
    won = len([p for p in completed if p.status == 'won'])
    return won / len(completed)


def get_probability_color(probability):
    """
    Get display color based on probability
    Higher probability = more green
    """
    if probability >= 0.7:
        return '#22c55e'  # Green
    elif probability >= 0.5:
        return '#eab308'  # Yellow
    else:
        return '#ef4444'  # Red


def get_status_color(status):
    """Get display color based on prediction status"""
    colors = {
        'won': '#22c55e',    # Green
        'lost': '#ef4444',   # Red
        'pending': '#3b82f6' # Blue
    }
    return colors.get(status, '#9ca3af')


def truncate_team_name(name, max_length=20):
    """Truncate long team names for display"""
    if len(name) <= max_length:
        return name
    return name[:max_length-3] + '...'
