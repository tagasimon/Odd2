"""
Odd 2 - Database Models
SQLAlchemy models for predictions, matches, payments, and user sessions
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Prediction(db.Model):
    """
    Prediction model - contains a combination of matches with total odds >= 2.0
    """
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_type = db.Column(db.String(10), nullable=False)  # 'vip' or 'free'
    total_odds = db.Column(db.Float, nullable=False)
    success_probability = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    status = db.Column(db.String(20), default='pending')  # 'pending', 'won', 'lost'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    matches = db.relationship('Match', backref='prediction', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='prediction', lazy=True)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'prediction_type': self.prediction_type,
            'total_odds': round(self.total_odds, 2),
            'success_probability': round(self.success_probability * 100, 1),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'matches': [m.to_dict() for m in self.matches]
        }


class Match(db.Model):
    """
    Individual match within a prediction
    """
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False)
    team_home = db.Column(db.String(100), nullable=False)
    team_away = db.Column(db.String(100), nullable=False)
    league = db.Column(db.String(100), nullable=False)
    match_time = db.Column(db.DateTime, nullable=False)
    bet_type = db.Column(db.String(20), nullable=False)  # 'Over 1.5', 'Over 2.5', etc.
    odds = db.Column(db.Float, nullable=False)
    result = db.Column(db.String(10), nullable=True)  # 'won', 'lost', or NULL if pending
    actual_goals = db.Column(db.Integer, nullable=True)  # Total goals scored
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'team_home': self.team_home,
            'team_away': self.team_away,
            'league': self.league,
            'match_time': self.match_time.isoformat() if self.match_time else None,
            'bet_type': self.bet_type,
            'odds': round(self.odds, 2),
            'result': self.result,
            'actual_goals': self.actual_goals
        }
    
    def get_over_threshold(self):
        """Extract the over threshold from bet type (e.g., 'Over 2.5' -> 2.5)"""
        try:
            return float(self.bet_type.replace('Over ', ''))
        except:
            return 0.5
    
    def check_result(self, total_goals):
        """
        Check if the bet won based on actual goals
        Returns: 'won' or 'lost'
        """
        threshold = self.get_over_threshold()
        self.actual_goals = total_goals
        self.result = 'won' if total_goals > threshold else 'lost'
        return self.result


class Payment(db.Model):
    """
    Payment records for VIP predictions
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(5), nullable=False)  # UGX, KES, TZS, RWF
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'failed'
    phone_number = db.Column(db.String(20), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'prediction_id': self.prediction_id,
            'amount': self.amount,
            'currency': self.currency,
            'transaction_id': self.transaction_id,
            'payment_status': self.payment_status,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None
        }


class UserSession(db.Model):
    """
    User sessions for VIP access (no login required)
    Sessions expire at the next prediction refresh (12 PM or 12 AM EAT)
    """
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_token = db.Column(db.String(100), unique=True, nullable=False)
    vip_prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=True)
    access_expires_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    vip_prediction = db.relationship('Prediction', backref='sessions')
    
    def is_valid(self):
        """Check if session is still valid"""
        if not self.access_expires_at:
            return False
        return datetime.utcnow() < self.access_expires_at
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'session_token': self.session_token,
            'vip_prediction_id': self.vip_prediction_id,
            'access_expires_at': self.access_expires_at.isoformat() if self.access_expires_at else None,
            'is_valid': self.is_valid()
        }


class ExchangeRate(db.Model):
    """
    Currency exchange rates (updated daily)
    """
    __tablename__ = 'exchange_rates'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_currency = db.Column(db.String(5), nullable=False, default='UGX')
    target_currency = db.Column(db.String(5), nullable=False)
    rate = db.Column(db.Float, nullable=False)  # How many target = 1 base
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'base': self.base_currency,
            'target': self.target_currency,
            'rate': self.rate,
            'updated_at': self.updated_at.isoformat()
        }
