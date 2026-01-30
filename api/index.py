"""
Vercel Serverless Function Entry Point
Wraps Flask app for Vercel deployment
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from datetime import datetime, timedelta

# Create minimal app first
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static',
            static_url_path='/static')

# Load config
try:
    from config import Config
    app.config.from_object(Config)
except Exception as e:
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-me')

# Database setup - use PostgreSQL on Vercel or in-memory SQLite for testing
database_url = os.environ.get('DATABASE_URL', '')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Use in-memory SQLite for serverless (limited persistence)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
try:
    from database.models import db, Prediction, Match, Payment, UserSession
    db.init_app(app)
    with app.app_context():
        db.create_all()
    DB_AVAILABLE = True
except Exception as e:
    print(f"Database init error: {e}")
    DB_AVAILABLE = False

# Import helpers
try:
    from utils.helpers import get_time_until_update, format_match_time
    from utils.geolocation import detect_user_location
    from payment.currency import get_vip_price
except Exception as e:
    print(f"Import error: {e}")


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main page with predictions"""
    try:
        from utils.geolocation import detect_user_location
        from payment.currency import get_vip_price
        from utils.helpers import get_time_until_update, format_match_time
        
        location = detect_user_location(request)
        currency = location['currency']
        vip_price = get_vip_price(currency)
        countdown = get_time_until_update()
        
        current_vip = None
        current_free = None
        has_vip_access = False
        vip_history = []
        free_history = []
        
        if DB_AVAILABLE:
            current_vip = Prediction.query.filter_by(
                prediction_type='vip',
                status='pending'
            ).order_by(Prediction.created_at.desc()).first()
            
            current_free = Prediction.query.filter_by(
                prediction_type='free',
                status='pending'
            ).order_by(Prediction.created_at.desc()).first()
            
            session_token = request.cookies.get('odd2_session')
            if session_token and current_vip:
                user_session = UserSession.query.filter_by(
                    session_token=session_token,
                    vip_prediction_id=current_vip.id
                ).first()
                if user_session and user_session.is_valid():
                    has_vip_access = True
        
        return render_template('index.html',
            current_vip=current_vip,
            current_free=current_free,
            has_vip_access=has_vip_access,
            vip_history=vip_history,
            free_history=free_history,
            vip_price=vip_price,
            countdown=countdown,
            currency=currency,
            format_match_time=format_match_time
        )
    except Exception as e:
        return jsonify({'error': str(e), 'type': 'index_error'}), 500


@app.route('/api/countdown')
def get_countdown():
    """API endpoint for countdown timer"""
    try:
        from utils.helpers import get_time_until_update
        countdown = get_time_until_update()
        return jsonify(countdown)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status')
def status():
    """Health check endpoint"""
    try:
        pred_count = 0
        if DB_AVAILABLE:
            pred_count = Prediction.query.filter_by(status='pending').count()
        return jsonify({
            'status': 'ok',
            'db_available': DB_AVAILABLE,
            'predictions': pred_count,
            'database_url': 'configured' if os.environ.get('DATABASE_URL') else 'not_configured'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/cron/generate-predictions', methods=['GET', 'POST'])
def cron_generate_predictions():
    """Cron endpoint for daily prediction generation"""
    cron_secret = os.environ.get('CRON_SECRET')
    if cron_secret:
        auth_header = request.headers.get('Authorization')
        if auth_header != f'Bearer {cron_secret}':
            return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        from prediction.generator import generate_and_save_predictions
        generate_and_save_predictions(app)
        return jsonify({'success': True, 'message': 'Predictions generated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/initiate-payment', methods=['POST'])
def initiate_payment():
    """Initiate VIP payment"""
    try:
        from payment.relworx import RelworxPayment
        from utils.geolocation import detect_user_location
        from payment.currency import get_vip_price
        
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'success': False, 'error': 'Phone number required'}), 400
        
        if not DB_AVAILABLE:
            return jsonify({'success': False, 'error': 'Database not available'}), 503
        
        current_vip = Prediction.query.filter_by(
            prediction_type='vip',
            status='pending'
        ).order_by(Prediction.created_at.desc()).first()
        
        if not current_vip:
            return jsonify({'success': False, 'error': 'No VIP prediction available'}), 404
        
        location = detect_user_location(request)
        currency = location['currency']
        vip_price = get_vip_price(currency)
        
        reference = f"ODD2-{current_vip.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        payment = Payment(
            prediction_id=current_vip.id,
            amount=vip_price['amount'],
            currency=currency,
            phone_number=phone_number,
            payment_status='pending'
        )
        db.session.add(payment)
        db.session.commit()
        
        relworx = RelworxPayment()
        callback_url = url_for('payment_webhook', _external=True)
        
        result = relworx.initiate_payment(
            amount=vip_price['amount'],
            currency=currency,
            phone_number=phone_number,
            reference=reference,
            callback_url=callback_url
        )
        
        if result['success']:
            payment.transaction_id = result.get('transaction_id')
            db.session.commit()
            return jsonify({
                'success': True,
                'message': result['message'],
                'transaction_id': result.get('transaction_id')
            })
        else:
            payment.payment_status = 'failed'
            db.session.commit()
            return jsonify({
                'success': False,
                'error': result.get('error', 'Payment failed')
            }), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/webhook/payment', methods=['POST'])
def payment_webhook():
    """Handle payment webhook from Relworx"""
    try:
        from payment.relworx import RelworxPayment, process_payment_callback
        
        signature = request.headers.get('X-Signature', '')
        relworx = RelworxPayment()
        
        if not relworx.verify_webhook(signature, request.data.decode()):
            return jsonify({'error': 'Invalid signature'}), 401
        
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        status = data.get('status')
        
        if transaction_id and status:
            success = process_payment_callback(transaction_id, status, app)
            return jsonify({'success': success})
        
        return jsonify({'error': 'Invalid data'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/check-payment/<transaction_id>')
def check_payment_status(transaction_id):
    """Check payment status"""
    try:
        if not DB_AVAILABLE:
            return jsonify({'status': 'error', 'error': 'Database not available'}), 503
            
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            return jsonify({'status': 'not_found'}), 404
        
        if payment.payment_status == 'completed':
            user_session = UserSession.query.filter_by(
                vip_prediction_id=payment.prediction_id
            ).order_by(UserSession.created_at.desc()).first()
            
            if user_session:
                response = make_response(jsonify({
                    'status': 'completed',
                    'redirect': url_for('index')
                }))
                response.set_cookie('odd2_session', user_session.session_token,
                    httponly=True,
                    max_age=86400,
                    samesite='Lax'
                )
                return response
        
        return jsonify({'status': payment.payment_status})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error', 'details': str(e)}), 500


# Vercel handler
handler = app
