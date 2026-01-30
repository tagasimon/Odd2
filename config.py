"""
Odd 2 - Configuration Settings
"""
import os
from dotenv import load_dotenv

# Load .env first, then .env.local to override with local values
load_dotenv('.env')
load_dotenv('.env.local', override=True)


class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///odd2.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Football Data API
    FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY', '')
    FOOTBALL_API_BASE_URL = 'https://api.football-data.org/v4'
    
    # Relworx Payment API
    RELWORX_API_KEY = os.getenv('RELWORX_API_KEY', '')
    RELWORX_API_SECRET = os.getenv('RELWORX_API_SECRET', '')
    RELWORX_WEBHOOK_SECRET = os.getenv('RELWORX_WEBHOOK_SECRET', '')
    RELWORX_ACCOUNT_NO = os.getenv('RELWORX_ACCOUNT_NO', '')
    RELWORX_API_BASE_URL = 'https://api.relworx.com/v1'
    # Proxy URL for static IP (to bypass Relworx IP whitelist)
    RELWORX_PROXY_URL = os.getenv('RELWORX_PROXY_URL', '')
    
    # Timezone (East Africa Time)
    TIMEZONE = os.getenv('TIMEZONE', 'Africa/Kampala')
    
    # VIP Pricing (base in UGX)
    VIP_PRICE_UGX = int(os.getenv('VIP_PRICE_UGX', 5000))
    
    # Exchange Rate API
    EXCHANGE_RATE_API_KEY = os.getenv('EXCHANGE_RATE_API_KEY', '')
    
    # Supported currencies with country codes
    SUPPORTED_CURRENCIES = {
        'UG': {'currency': 'UGX', 'name': 'Ugandan Shilling'},
        'KE': {'currency': 'KES', 'name': 'Kenyan Shilling'},
        'TZ': {'currency': 'TZS', 'name': 'Tanzanian Shilling'},
        'RW': {'currency': 'RWF', 'name': 'Rwandan Franc'},
        'BI': {'currency': 'BIF', 'name': 'Burundian Franc'},
    }
    
    # Default currency (for fallback)
    DEFAULT_CURRENCY = 'UGX'
    DEFAULT_COUNTRY = 'UG'
    
    # Prediction update times (in 24h format, EAT timezone)
    UPDATE_HOURS = [0, 12]  # 12:00 AM and 12:00 PM
    
    # History days to show
    HISTORY_DAYS = 7
    
    # Minimum odds for predictions
    MIN_TOTAL_ODDS = 2.0
