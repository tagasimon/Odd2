"""
Odd 2 - Currency Conversion
Handles exchange rates and price conversion for East African currencies
"""
import requests
from datetime import datetime
from config import Config


def get_exchange_rate(from_currency, to_currency):
    """
    Get exchange rate between two currencies
    
    Args:
        from_currency: Source currency code (e.g., 'UGX')
        to_currency: Target currency code (e.g., 'KES')
        
    Returns:
        Exchange rate (float) or None if failed
    """
    from database.models import db, ExchangeRate
    from flask import current_app
    
    if from_currency == to_currency:
        return 1.0
    
    # Try to get from database first
    try:
        with current_app.app_context():
            rate = ExchangeRate.query.filter_by(
                base_currency=from_currency,
                target_currency=to_currency
            ).first()
            
            if rate:
                return rate.rate
    except:
        pass
    
    # Fallback rates if database not available
    fallback_rates = {
        ('UGX', 'KES'): 0.035,
        ('UGX', 'TZS'): 0.68,
        ('UGX', 'RWF'): 0.33,
        ('UGX', 'BIF'): 0.76,
    }
    
    return fallback_rates.get((from_currency, to_currency), 1.0)


def convert_price(amount_ugx, target_currency):
    """
    Convert UGX price to target currency
    
    Args:
        amount_ugx: Amount in Ugandan Shillings
        target_currency: Target currency code
        
    Returns:
        Converted amount (rounded to whole number)
    """
    if target_currency == 'UGX':
        return int(amount_ugx)
    
    rate = get_exchange_rate('UGX', target_currency)
    converted = amount_ugx * rate
    
    # Round to sensible amounts based on currency
    if target_currency in ['KES', 'TZS', 'RWF', 'BIF']:
        # Round to nearest 10
        return int(round(converted / 10) * 10)
    
    return int(round(converted))


def get_vip_price(currency='UGX'):
    """
    Get VIP prediction price in specified currency
    
    Args:
        currency: Currency code
        
    Returns:
        dict with amount and formatted string
    """
    base_price = Config.VIP_PRICE_UGX
    
    if currency == 'UGX':
        return {
            'amount': base_price,
            'currency': 'UGX',
            'formatted': f"UGX {base_price:,}"
        }
    
    converted = convert_price(base_price, currency)
    
    return {
        'amount': converted,
        'currency': currency,
        'formatted': f"{currency} {converted:,}"
    }


def update_exchange_rates(app):
    """
    Fetch and update exchange rates from API
    
    Args:
        app: Flask application instance
    """
    from database.models import db, ExchangeRate
    
    api_key = Config.EXCHANGE_RATE_API_KEY
    
    # If no API key, use fallback rates
    if not api_key:
        print("   No exchange rate API key, using fallback rates")
        return
    
    try:
        # Free tier: exchangerate-api.com
        response = requests.get(
            f'https://v6.exchangerate-api.com/v6/{api_key}/latest/UGX',
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   API error: {response.status_code}")
            return
        
        data = response.json()
        rates = data.get('conversion_rates', {})
        
        with app.app_context():
            for currency in ['UGX', 'KES', 'TZS', 'RWF', 'BIF']:
                if currency in rates:
                    existing = ExchangeRate.query.filter_by(
                        base_currency='UGX',
                        target_currency=currency
                    ).first()
                    
                    if existing:
                        existing.rate = rates[currency]
                        existing.updated_at = datetime.utcnow()
                    else:
                        new_rate = ExchangeRate(
                            base_currency='UGX',
                            target_currency=currency,
                            rate=rates[currency]
                        )
                        db.session.add(new_rate)
            
            db.session.commit()
            print("   Exchange rates updated from API")
            
    except Exception as e:
        print(f"   Exchange rate update error: {e}")


def get_currency_symbol(currency_code):
    """Get the symbol for a currency"""
    symbols = {
        'UGX': 'USh',
        'KES': 'KSh',
        'TZS': 'TSh',
        'RWF': 'FRw',
        'BIF': 'FBu'
    }
    return symbols.get(currency_code, currency_code)
