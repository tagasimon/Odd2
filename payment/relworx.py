"""
Odd 2 - Relworx Payment Integration
Mobile money payment processing via Relworx API
"""
import requests
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from config import Config


class RelworxPayment:
    """
    Relworx Payment API integration
    Supports mobile money payments in UGX, KES, TZS, RWF
    """
    
    def __init__(self):
        self.api_key = Config.RELWORX_API_KEY
        self.api_secret = Config.RELWORX_API_SECRET
        self.webhook_secret = Config.RELWORX_WEBHOOK_SECRET
        self.base_url = Config.RELWORX_API_BASE_URL
    
    def _generate_signature(self, payload):
        """Generate HMAC signature for API request"""
        message = json.dumps(payload, separators=(',', ':'))
        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_request(self, endpoint, method='POST', data=None):
        """Make authenticated API request"""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        if data:
            headers['X-Signature'] = self._generate_signature(data)
        
        try:
            if method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            else:
                response = requests.get(url, headers=headers, timeout=30)
            
            return {
                'success': response.status_code in [200, 201],
                'status_code': response.status_code,
                'data': response.json() if response.content else {}
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def initiate_payment(self, amount, currency, phone_number, reference, callback_url):
        """
        Initiate a mobile money payment
        
        Args:
            amount: Payment amount
            currency: Currency code (UGX, KES, etc.)
            phone_number: Customer phone number
            reference: Unique transaction reference
            callback_url: URL for payment confirmation webhook
            
        Returns:
            dict with success status and transaction details
        """
        # Map currency to payment method
        payment_methods = {
            'UGX': 'mtn_ug',      # MTN Mobile Money Uganda
            'KES': 'mpesa_ke',    # M-Pesa Kenya
            'TZS': 'tigopesa_tz', # Tigo Pesa Tanzania
            'RWF': 'mtn_rw',      # MTN Mobile Money Rwanda
        }
        
        payment_method = payment_methods.get(currency, 'mtn_ug')
        
        payload = {
            'amount': int(amount),
            'currency': currency,
            'phone_number': phone_number,
            'payment_method': payment_method,
            'reference': reference,
            'callback_url': callback_url,
            'description': f'Odd 2 VIP Prediction Access'
        }
        
        result = self._make_request('/payments/collect', 'POST', payload)
        
        if result.get('success'):
            return {
                'success': True,
                'transaction_id': result['data'].get('transaction_id'),
                'status': result['data'].get('status', 'pending'),
                'message': 'Payment initiated. Please complete on your phone.'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Payment initiation failed')
            }
    
    def check_payment_status(self, transaction_id):
        """
        Check the status of a payment
        
        Args:
            transaction_id: Relworx transaction ID
            
        Returns:
            Payment status (pending, completed, failed)
        """
        result = self._make_request(f'/payments/{transaction_id}', 'GET')
        
        if result.get('success'):
            return {
                'success': True,
                'status': result['data'].get('status', 'pending'),
                'transaction_id': transaction_id
            }
        
        return {
            'success': False,
            'status': 'unknown',
            'error': result.get('error')
        }
    
    def verify_webhook(self, signature, payload):
        """
        Verify webhook signature from Relworx
        
        Args:
            signature: X-Signature header from webhook
            payload: Raw request body
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            return True  # Skip verification if no secret configured
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)


def process_payment_callback(transaction_id, status, app):
    """
    Process a payment callback from Relworx
    
    Args:
        transaction_id: Relworx transaction ID
        status: Payment status (completed, failed)
        app: Flask application instance
        
    Returns:
        Success boolean
    """
    from database.models import db, Payment, UserSession
    from utils.helpers import get_next_update_time, generate_session_token
    
    with app.app_context():
        # Find the payment record
        payment = Payment.query.filter_by(transaction_id=transaction_id).first()
        
        if not payment:
            print(f"⚠️  Payment not found: {transaction_id}")
            return False
        
        # Update payment status
        payment.payment_status = status
        
        if status == 'completed':
            # Find or create user session
            session = UserSession.query.filter_by(
                vip_prediction_id=payment.prediction_id
            ).first()
            
            if not session:
                session = UserSession(
                    session_token=generate_session_token(),
                    vip_prediction_id=payment.prediction_id,
                    access_expires_at=get_next_update_time()
                )
                db.session.add(session)
            else:
                session.access_expires_at = get_next_update_time()
            
            print(f"✅ Payment completed: {transaction_id}")
        else:
            print(f"❌ Payment failed: {transaction_id}")
        
        db.session.commit()
        return status == 'completed'


def create_demo_payment(prediction_id, app):
    """
    Create a demo payment for testing (bypasses actual payment)
    
    Args:
        prediction_id: VIP prediction ID to unlock
        app: Flask application instance
        
    Returns:
        Session token for VIP access
    """
    from database.models import db, Payment, UserSession
    from utils.helpers import get_next_update_time, generate_session_token
    
    with app.app_context():
        # Create demo payment record
        payment = Payment(
            prediction_id=prediction_id,
            amount=Config.VIP_PRICE_UGX,
            currency='UGX',
            transaction_id=f'DEMO-{datetime.utcnow().timestamp()}',
            payment_status='completed'
        )
        db.session.add(payment)
        
        # Create session
        session_token = generate_session_token()
        session = UserSession(
            session_token=session_token,
            vip_prediction_id=prediction_id,
            access_expires_at=get_next_update_time()
        )
        db.session.add(session)
        
        db.session.commit()
        
        print(f"✅ Demo payment created for prediction #{prediction_id}")
        return session_token
