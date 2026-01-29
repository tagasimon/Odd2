"""
Odd 2 - Geolocation Utilities
IP-based country and currency detection
"""
import requests
from config import Config


def get_country_from_ip(ip_address):
    """
    Detect country from IP address using ip-api.com (free tier)
    
    Args:
        ip_address: Client IP address
        
    Returns:
        dict with country_code and country_name, or defaults if detection fails
    """
    # Default to Uganda if detection fails
    default = {
        'country_code': Config.DEFAULT_COUNTRY,
        'country_name': 'Uganda',
        'currency': Config.DEFAULT_CURRENCY
    }
    
    # Skip for localhost/private IPs
    if ip_address in ['127.0.0.1', 'localhost', '::1'] or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
        return default
    
    try:
        # ip-api.com free tier (limited to 45 requests/minute)
        response = requests.get(
            f'http://ip-api.com/json/{ip_address}',
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country_code = data.get('countryCode', Config.DEFAULT_COUNTRY)
                country_name = data.get('country', 'Uganda')
                
                # Get currency for this country
                currency_info = Config.SUPPORTED_CURRENCIES.get(
                    country_code,
                    {'currency': Config.DEFAULT_CURRENCY, 'name': 'Ugandan Shilling'}
                )
                
                return {
                    'country_code': country_code,
                    'country_name': country_name,
                    'currency': currency_info['currency']
                }
        
        return default
        
    except Exception as e:
        print(f"Geolocation error: {e}")
        return default


def get_currency_for_country(country_code):
    """
    Get the currency code for a given country
    
    Args:
        country_code: ISO 2-letter country code (e.g., 'UG', 'KE')
        
    Returns:
        Currency code (e.g., 'UGX', 'KES')
    """
    currency_info = Config.SUPPORTED_CURRENCIES.get(
        country_code,
        {'currency': Config.DEFAULT_CURRENCY}
    )
    return currency_info['currency']


def get_client_ip(request):
    """
    Get the real client IP from a Flask request
    Handles proxies and load balancers
    
    Args:
        request: Flask request object
        
    Returns:
        Client IP address string
    """
    # Check for forwarded headers (when behind proxy)
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs, first is the client
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    return request.remote_addr


def detect_user_location(request):
    """
    Detect user's country and currency from request
    
    Args:
        request: Flask request object
        
    Returns:
        dict with country_code, country_name, currency
    """
    ip = get_client_ip(request)
    return get_country_from_ip(ip)
