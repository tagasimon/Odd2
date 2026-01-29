"""
Odd 2 - Scheduled Tasks
APScheduler configuration for automated prediction updates
"""
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from config import Config


def create_scheduler(app):
    """
    Create and configure the task scheduler
    
    Args:
        app: Flask application instance
        
    Returns:
        Configured BackgroundScheduler instance
    """
    scheduler = BackgroundScheduler(
        timezone=pytz.timezone(Config.TIMEZONE)
    )
    
    # Task 1: Generate new predictions at 12 PM and 12 AM EAT
    scheduler.add_job(
        func=lambda: run_prediction_job(app),
        trigger=CronTrigger(hour='0,12', minute=0),
        id='generate_predictions',
        name='Generate daily predictions',
        replace_existing=True
    )
    
    # Task 2: Update match results (every hour)
    scheduler.add_job(
        func=lambda: run_results_update(app),
        trigger=CronTrigger(minute=30),  # Every hour at :30
        id='update_results',
        name='Update match results',
        replace_existing=True
    )
    
    # Task 3: Update exchange rates (daily at 6 AM)
    scheduler.add_job(
        func=lambda: run_exchange_rate_update(app),
        trigger=CronTrigger(hour=6, minute=0),
        id='update_exchange_rates',
        name='Update exchange rates',
        replace_existing=True
    )
    
    # Task 4: Clean up expired sessions (every 2 hours)
    scheduler.add_job(
        func=lambda: cleanup_expired_sessions(app),
        trigger=CronTrigger(hour='*/2', minute=15),
        id='cleanup_sessions',
        name='Cleanup expired sessions',
        replace_existing=True
    )
    
    return scheduler


def run_prediction_job(app):
    """Generate new predictions and expire old ones"""
    from prediction.generator import generate_and_save_predictions
    
    print(f"\n{'='*50}")
    print(f"🕐 Running prediction job at {datetime.now()}")
    print('='*50)
    
    try:
        generate_and_save_predictions(app)
        expire_vip_sessions(app)
        print("✅ Prediction job completed successfully")
    except Exception as e:
        print(f"❌ Prediction job failed: {e}")


def run_results_update(app):
    """Check for completed matches and update results"""
    from database.models import db, Prediction, Match
    from prediction.data_fetcher import FootballDataFetcher
    
    print(f"🔄 Checking for completed matches...")
    
    with app.app_context():
        fetcher = FootballDataFetcher()
        
        # Get pending predictions with matches that might be completed
        pending_preds = Prediction.query.filter_by(status='pending').all()
        
        for pred in pending_preds:
            all_completed = True
            all_won = True
            
            for match in pred.matches:
                if match.result:
                    # Already has result
                    if match.result == 'lost':
                        all_won = False
                    continue
                
                # Check if match should be completed (match time + 3 hours)
                if match.match_time:
                    match_end = match.match_time.replace(tzinfo=None)
                    from datetime import timedelta
                    if datetime.utcnow() < match_end + timedelta(hours=3):
                        all_completed = False
                        continue
                
                # Try to get result from API
                if match.id:  # Need API match ID
                    result_data = fetcher.get_match_result(match.id)
                    if result_data:
                        match.check_result(result_data['total_goals'])
                        if match.result == 'lost':
                            all_won = False
                    else:
                        all_completed = False
            
            # Update prediction status if all matches completed
            if all_completed:
                pred.status = 'won' if all_won else 'lost'
                pred.completed_at = datetime.utcnow()
                print(f"   Prediction #{pred.id} marked as {pred.status}")
        
        db.session.commit()


def run_exchange_rate_update(app):
    """Update currency exchange rates"""
    from payment.currency import update_exchange_rates
    
    print(f"💱 Updating exchange rates...")
    
    try:
        update_exchange_rates(app)
        print("✅ Exchange rates updated")
    except Exception as e:
        print(f"⚠️  Exchange rate update failed: {e}")


def expire_vip_sessions(app):
    """Expire all VIP access sessions at prediction refresh"""
    from database.models import db, UserSession
    
    with app.app_context():
        sessions = UserSession.query.filter(
            UserSession.access_expires_at != None
        ).all()
        
        count = 0
        for session in sessions:
            session.access_expires_at = datetime.utcnow()
            count += 1
        
        db.session.commit()
        print(f"   Expired {count} VIP sessions")


def cleanup_expired_sessions(app):
    """Remove old expired sessions from database"""
    from database.models import db, UserSession
    from datetime import timedelta
    
    with app.app_context():
        # Delete sessions older than 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        old_sessions = UserSession.query.filter(
            UserSession.created_at < cutoff
        ).delete()
        
        db.session.commit()
        print(f"🧹 Cleaned up {old_sessions} old sessions")


def manually_trigger_predictions(app):
    """
    Manually trigger prediction generation (for testing/admin)
    
    Args:
        app: Flask application instance
    """
    run_prediction_job(app)
