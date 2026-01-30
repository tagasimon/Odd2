"""
Vercel Serverless Function Entry Point
Wraps Flask app for Vercel deployment
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response
from flask_wtf.csrf import CSRFProtect
from database.models import db, Prediction, Match, Payment, UserSession
from config import Config
from utils.helpers import get_time_until_update, generate_session_token, format_match_time
from utils.geolocation import detect_user_location
from payment.currency import get_vip_price
from payment.relworx import RelworxPayment, create_demo_payment
from datetime import datetime, timedelta


def create_app():
    """Application factory for Vercel"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static',
                static_url_path='/static')
    app.config.from_object(Config)
    
    # Use PostgreSQL for Vercel (via DATABASE_URL) or SQLite for local
    database_url = os.environ.get('DATABASE_URL', Config.SQLALCHEMY_DATABASE_URI)
    # Fix for Heroku/Vercel PostgreSQL URL format
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Exempt webhooks from CSRF
    csrf.exempt('payment_webhook')
    
    return app, csrf


app, csrf = create_app()


# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    """Main page with predictions and history"""
    location = detect_user_location(request)
    currency = location['currency']
    vip_price = get_vip_price(currency)
    
    current_vip = Prediction.query.filter_by(
        prediction_type='vip',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    current_free = Prediction.query.filter_by(
        prediction_type='free',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    session_token = request.cookies.get('odd2_session')
    has_vip_access = False
    
    if session_token and current_vip:
        user_session = UserSession.query.filter_by(
            session_token=session_token,
            vip_prediction_id=current_vip.id
        ).first()
        if user_session and user_session.is_valid():
            has_vip_access = True
    
    seven_days_ago = datetime.utcnow() - timedelta(days=Config.HISTORY_DAYS)
    
    vip_history = Prediction.query.filter(
        Prediction.prediction_type == 'vip',
        Prediction.status.in_(['won', 'lost']),
        Prediction.created_at >= seven_days_ago
    ).order_by(Prediction.created_at.desc()).limit(10).all()
    
    free_history = Prediction.query.filter(
        Prediction.prediction_type == 'free',
        Prediction.status.in_(['won', 'lost']),
        Prediction.created_at >= seven_days_ago
    ).order_by(Prediction.created_at.desc()).limit(10).all()
    
    countdown = get_time_until_update()
    
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


@app.route('/api/countdown')
def get_countdown():
    """API endpoint for countdown timer"""
    countdown = get_time_until_update()
    return jsonify(countdown)


# ============================================================================
# ROUTES - Payment
# ============================================================================

@app.route('/api/initiate-payment', methods=['POST'])
@csrf.exempt
def initiate_payment():
    """Initiate VIP payment"""
    data = request.get_json()
    phone_number = data.get('phone_number')
    
    if not phone_number:
        return jsonify({'success': False, 'error': 'Phone number required'}), 400
    
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


@app.route('/webhook/payment', methods=['POST'])
@csrf.exempt
def payment_webhook():
    """Handle payment webhook from Relworx"""
    from payment.relworx import process_payment_callback
    
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


@app.route('/api/check-payment/<transaction_id>')
def check_payment_status(transaction_id):
    """Check payment status"""
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


# ============================================================================
# ROUTES - Cron Jobs (Vercel)
# ============================================================================

@app.route('/api/cron/generate-predictions', methods=['GET', 'POST'])
def cron_generate_predictions():
    """Cron endpoint for daily prediction generation"""
    # Verify cron secret if configured
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


@app.route('/api/status')
def status():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'predictions': Prediction.query.filter_by(status='pending').count()
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error'), 500


# Vercel handler
handler = app
