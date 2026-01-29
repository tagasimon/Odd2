"""
Odd 2 - Database Initialization
Creates tables and seeds initial data
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from database.models import db, Prediction, Match, Payment, UserSession, ExchangeRate
from config import Config


def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def init_database():
    """Initialize the database with all tables"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Seed default exchange rates (approximate rates)
        seed_exchange_rates()
        
        print("✅ Database initialized successfully!")
        print(f"   Database location: {app.config['SQLALCHEMY_DATABASE_URI']}")


def seed_exchange_rates():
    """Seed default exchange rates"""
    # Default exchange rates from UGX to other currencies
    # These will be updated daily by the scheduler
    default_rates = [
        {'base': 'UGX', 'target': 'UGX', 'rate': 1.0},
        {'base': 'UGX', 'target': 'KES', 'rate': 0.035},  # ~1 UGX = 0.035 KES
        {'base': 'UGX', 'target': 'TZS', 'rate': 0.68},   # ~1 UGX = 0.68 TZS
        {'base': 'UGX', 'target': 'RWF', 'rate': 0.33},   # ~1 UGX = 0.33 RWF
        {'base': 'UGX', 'target': 'BIF', 'rate': 0.76},   # ~1 UGX = 0.76 BIF
    ]
    
    for rate_data in default_rates:
        existing = ExchangeRate.query.filter_by(
            base_currency=rate_data['base'],
            target_currency=rate_data['target']
        ).first()
        
        if not existing:
            rate = ExchangeRate(
                base_currency=rate_data['base'],
                target_currency=rate_data['target'],
                rate=rate_data['rate']
            )
            db.session.add(rate)
    
    db.session.commit()
    print("   Exchange rates seeded")


def reset_database():
    """Drop all tables and recreate (for development only)"""
    app = create_app()
    
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_exchange_rates()
        print("✅ Database reset successfully!")


if __name__ == '__main__':
    init_database()
