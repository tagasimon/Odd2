"""
Odd 2 - Main Flask Application
Football Predictions Website with AI-powered "over goals" predictions
Version: 1.0.0 - January 2026
"""
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response, session
from flask_wtf.csrf import CSRFProtect
from database.models import db, Prediction, Match, Payment, UserSession
from config import Config
from utils.helpers import get_time_until_update, generate_session_token, format_match_time
from utils.geolocation import detect_user_location
from payment.currency import get_vip_price
from payment.relworx import RelworxPayment, create_demo_payment


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    csrf = CSRFProtect(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Exempt webhook from CSRF
    csrf.exempt('payment_webhook')
    
    return app, csrf


app, csrf = create_app()


# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    """Main page with predictions and history"""
    # Get user location for currency
    location = detect_user_location(request)
    currency = location['currency']
    
    # Get VIP price in user's currency
    vip_price = get_vip_price(currency)
    
    # Get current predictions
    current_vip = Prediction.query.filter_by(
        prediction_type='vip',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    current_free = Prediction.query.filter_by(
        prediction_type='free',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    # Check if user has VIP access
    session_token = request.cookies.get('odd2_session')
    has_vip_access = False
    
    if session_token and current_vip:
        user_session = UserSession.query.filter_by(
            session_token=session_token,
            vip_prediction_id=current_vip.id
        ).first()
        if user_session and user_session.is_valid():
            has_vip_access = True
    
    # Get history (last 7 days)
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
    
    # Get countdown to next update
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
    
    # Get current VIP prediction
    current_vip = Prediction.query.filter_by(
        prediction_type='vip',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    if not current_vip:
        return jsonify({'success': False, 'error': 'No VIP prediction available'}), 404
    
    # Get user location and price
    location = detect_user_location(request)
    currency = location['currency']
    vip_price = get_vip_price(currency)
    
    # Generate unique reference
    reference = f"ODD2-{current_vip.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Create payment record
    payment = Payment(
        prediction_id=current_vip.id,
        amount=vip_price['amount'],
        currency=currency,
        phone_number=phone_number,
        payment_status='pending'
    )
    db.session.add(payment)
    db.session.commit()
    
    # Initiate payment via Relworx
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


@app.route('/api/demo-payment', methods=['POST'])
@csrf.exempt
def demo_payment():
    """Demo payment for testing (bypasses actual payment)"""
    # Get current VIP prediction
    current_vip = Prediction.query.filter_by(
        prediction_type='vip',
        status='pending'
    ).order_by(Prediction.created_at.desc()).first()
    
    if not current_vip:
        return jsonify({'success': False, 'error': 'No VIP prediction available'}), 404
    
    # Create demo payment and session
    session_token = create_demo_payment(current_vip.id, app)
    
    # Set session cookie
    response = make_response(jsonify({
        'success': True,
        'message': 'Demo payment successful! VIP prediction unlocked.'
    }))
    response.set_cookie('odd2_session', session_token, 
        httponly=True, 
        max_age=86400,  # 24 hours
        samesite='Lax'
    )
    
    return response


@app.route('/webhook/payment', methods=['POST'])
@csrf.exempt
def payment_webhook():
    """Handle payment webhook from Relworx"""
    from payment.relworx import process_payment_callback
    
    # Verify webhook signature
    signature = request.headers.get('X-Signature', '')
    relworx = RelworxPayment()
    
    if not relworx.verify_webhook(signature, request.data.decode()):
        return jsonify({'error': 'Invalid signature'}), 401
    
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    status = data.get('status')  # 'completed' or 'failed'
    
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
        # Get session token
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
# ROUTES - Admin/Debug
# ============================================================================

@app.route('/admin/generate-predictions', methods=['POST'])
def admin_generate():
    """Manually trigger prediction generation (for testing)"""
    from prediction.scheduler import manually_trigger_predictions
    
    try:
        manually_trigger_predictions(app)
        return jsonify({'success': True, 'message': 'Predictions generated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/admin/status')
def admin_status():
    """Check system status"""
    from prediction.data_fetcher import FootballDataFetcher
    
    fetcher = FootballDataFetcher()
    
    # Count predictions
    total_preds = Prediction.query.count()
    pending_preds = Prediction.query.filter_by(status='pending').count()
    
    # Check API
    api_configured = bool(Config.FOOTBALL_API_KEY)
    payment_configured = bool(Config.RELWORX_API_KEY)
    
    return jsonify({
        'database': {
            'total_predictions': total_preds,
            'pending_predictions': pending_preds
        },
        'api': {
            'football_api_configured': api_configured,
            'payment_api_configured': payment_configured
        },
        'config': {
            'timezone': Config.TIMEZONE,
            'vip_price_ugx': Config.VIP_PRICE_UGX,
            'update_hours': Config.UPDATE_HOURS
        }
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


# ============================================================================
# SCHEDULER SETUP
# ============================================================================

def start_scheduler():
    """Start the background scheduler"""
    from prediction.scheduler import create_scheduler
    
    scheduler = create_scheduler(app)
    scheduler.start()
    print("✅ Scheduler started")
    return scheduler


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Initialize database
    with app.app_context():
        from database.init_db import seed_exchange_rates
        db.create_all()
        seed_exchange_rates()
        print("✅ Database initialized")
    
    # Generate initial predictions if none exist
    with app.app_context():
        if Prediction.query.count() == 0:
            print("📋 Generating initial predictions...")
            from prediction.generator import generate_and_save_predictions
            generate_and_save_predictions(app)
    
    # Start scheduler
    scheduler = start_scheduler()
    
    # Run Flask app
    print("\n" + "="*50)
    print("🚀 Odd 2 Football Predictions")
    print("   http://127.0.0.1:5001")
    print("="*50 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("\n👋 Server stopped")
