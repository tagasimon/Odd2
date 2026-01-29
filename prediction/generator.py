"""
Odd 2 - Prediction Generator
Generates optimal bet combinations with odds >= 2.0
"""
from itertools import combinations
from datetime import datetime
from config import Config
from prediction.data_fetcher import FootballDataFetcher
from prediction.analyzer import MatchAnalyzer, OddsEstimator


class PredictionGenerator:
    """
    Generates optimal bet combinations for "over goals" predictions
    Finds combinations with total odds >= 2.0 and ranks by success probability
    """
    
    def __init__(self):
        self.fetcher = FootballDataFetcher()
        self.analyzer = MatchAnalyzer(self.fetcher)
        self.min_total_odds = Config.MIN_TOTAL_ODDS
    
    def generate_predictions(self):
        """
        Main method to generate VIP and Free predictions
        
        Returns:
            dict with 'vip' and 'free' prediction data, or None if no valid combinations
        """
        print("🔄 Starting prediction generation...")
        
        # Step 1: Fetch upcoming matches
        matches = self.fetcher.get_upcoming_matches(days=2)
        print(f"   Found {len(matches)} upcoming matches")
        
        if not matches:
            print("⚠️  No matches found")
            return self._generate_demo_predictions()
        
        # Step 2: Analyze each match
        analyzed_matches = []
        for match in matches[:20]:  # Limit to 20 matches for performance
            analysis = self._analyze_match(match)
            if analysis:
                analyzed_matches.append(analysis)
        
        print(f"   Analyzed {len(analyzed_matches)} matches")
        
        if len(analyzed_matches) < 2:
            print("⚠️  Not enough matches for combinations")
            return self._generate_demo_predictions()
        
        # Step 3: Generate all valid combinations
        combinations_list = self._generate_combinations(analyzed_matches)
        print(f"   Generated {len(combinations_list)} valid combinations")
        
        if not combinations_list:
            print("⚠️  No valid combinations found")
            return self._generate_demo_predictions()
        
        # Step 4: Rank combinations by success probability
        ranked = sorted(combinations_list, key=lambda x: x['success_probability'], reverse=True)
        
        # Step 5: Select VIP (highest probability) and Free (second best)
        vip = ranked[0]
        free = ranked[1] if len(ranked) > 1 else ranked[0]
        
        print(f"✅ Generated predictions:")
        print(f"   VIP: {len(vip['matches'])} matches, {vip['total_odds']:.2f} odds, {vip['success_probability']*100:.1f}% probability")
        print(f"   Free: {len(free['matches'])} matches, {free['total_odds']:.2f} odds, {free['success_probability']*100:.1f}% probability")
        
        return {
            'vip': vip,
            'free': free
        }
    
    def _analyze_match(self, match):
        """
        Analyze a single match and determine the best bet
        
        Returns:
            dict with match info and best bet, or None if not suitable
        """
        try:
            # Get goal predictions
            predictions = self.analyzer.analyze_match(match)
            
            # Find best bet type
            best_bet = self.analyzer.get_best_bet_type(predictions, min_prob=0.50)
            
            if not best_bet:
                return None
            
            # Estimate odds
            odds = OddsEstimator.estimate_over_odds(
                best_bet['threshold'],
                best_bet['probability']
            )
            
            # Only include if odds are worthwhile (>= 1.15)
            if odds < 1.15:
                return None
            
            return {
                'match_id': match.get('id'),
                'home_team': match['home_team'],
                'away_team': match['away_team'],
                'league': match['competition']['name'],
                'match_time': match['match_time'],
                'bet_type': best_bet['bet_type'],
                'odds': odds,
                'probability': best_bet['probability']
            }
            
        except Exception as e:
            print(f"   Error analyzing match: {e}")
            return None
    
    def _generate_combinations(self, matches, min_size=2, max_size=5):
        """
        Generate all valid bet combinations with total odds >= 2.0
        
        Args:
            matches: List of analyzed match dicts
            min_size: Minimum number of matches in combination
            max_size: Maximum number of matches in combination
            
        Returns:
            List of valid combinations
        """
        valid_combinations = []
        
        # Try combinations of different sizes
        for size in range(min_size, min(max_size + 1, len(matches) + 1)):
            for combo in combinations(matches, size):
                # Calculate total odds
                total_odds = 1.0
                for match in combo:
                    total_odds *= match['odds']
                
                # Check if meets minimum odds requirement
                if total_odds >= self.min_total_odds:
                    # Calculate combined success probability
                    success_prob = self.analyzer.calculate_combined_probability(
                        [{'probability': m['probability']} for m in combo]
                    )
                    
                    valid_combinations.append({
                        'matches': list(combo),
                        'total_odds': round(total_odds, 2),
                        'success_probability': success_prob
                    })
        
        return valid_combinations
    
    def _generate_demo_predictions(self):
        """
        Generate demo predictions when no real data is available
        Used for testing and when API is unavailable
        """
        from datetime import timedelta
        
        print("📋 Generating demo predictions (no API data available)")
        
        now = datetime.utcnow()
        
        demo_matches = [
            {
                'home_team': 'Manchester City',
                'away_team': 'Liverpool',
                'league': 'Premier League',
                'match_time': (now + timedelta(hours=3)).isoformat(),
                'bet_type': 'Over 2.5',
                'odds': 1.65,
                'probability': 0.62
            },
            {
                'home_team': 'Bayern Munich',
                'away_team': 'Borussia Dortmund',
                'league': 'Bundesliga',
                'match_time': (now + timedelta(hours=5)).isoformat(),
                'bet_type': 'Over 2.5',
                'odds': 1.55,
                'probability': 0.65
            },
            {
                'home_team': 'Real Madrid',
                'away_team': 'Barcelona',
                'league': 'La Liga',
                'match_time': (now + timedelta(hours=7)).isoformat(),
                'bet_type': 'Over 1.5',
                'odds': 1.35,
                'probability': 0.72
            },
            {
                'home_team': 'Inter Milan',
                'away_team': 'AC Milan',
                'league': 'Serie A',
                'match_time': (now + timedelta(hours=8)).isoformat(),
                'bet_type': 'Over 2.5',
                'odds': 1.75,
                'probability': 0.58
            },
            {
                'home_team': 'PSG',
                'away_team': 'Marseille',
                'league': 'Ligue 1',
                'match_time': (now + timedelta(hours=9)).isoformat(),
                'bet_type': 'Over 2.5',
                'odds': 1.60,
                'probability': 0.63
            }
        ]
        
        # VIP prediction: 2 matches with highest combined probability
        vip_matches = demo_matches[:2]
        vip_odds = vip_matches[0]['odds'] * vip_matches[1]['odds']
        vip_prob = vip_matches[0]['probability'] * vip_matches[1]['probability']
        
        # Free prediction: Different 2 matches
        free_matches = demo_matches[2:4]
        free_odds = free_matches[0]['odds'] * free_matches[1]['odds']
        free_prob = free_matches[0]['probability'] * free_matches[1]['probability']
        
        return {
            'vip': {
                'matches': vip_matches,
                'total_odds': round(vip_odds, 2),
                'success_probability': round(vip_prob, 3)
            },
            'free': {
                'matches': free_matches,
                'total_odds': round(free_odds, 2),
                'success_probability': round(free_prob, 3)
            }
        }


def generate_and_save_predictions(app):
    """
    Generate predictions and save to database
    Called by the scheduler at 12 PM and 12 AM EAT
    
    Args:
        app: Flask application instance
    """
    from database.models import db, Prediction, Match
    from utils.helpers import get_next_update_time
    
    with app.app_context():
        generator = PredictionGenerator()
        predictions = generator.generate_predictions()
        
        if not predictions:
            print("❌ Failed to generate predictions")
            return
        
        # Mark old pending predictions as expired
        old_predictions = Prediction.query.filter_by(status='pending').all()
        for pred in old_predictions:
            pred.status = 'expired'
        
        # Save VIP prediction
        vip = predictions['vip']
        vip_prediction = Prediction(
            prediction_type='vip',
            total_odds=vip['total_odds'],
            success_probability=vip['success_probability'],
            status='pending'
        )
        db.session.add(vip_prediction)
        db.session.flush()  # Get ID for matches
        
        # Add VIP matches
        for match_data in vip['matches']:
            match = Match(
                prediction_id=vip_prediction.id,
                team_home=match_data['home_team'],
                team_away=match_data['away_team'],
                league=match_data['league'],
                match_time=datetime.fromisoformat(match_data['match_time'].replace('Z', '+00:00')),
                bet_type=match_data['bet_type'],
                odds=match_data['odds']
            )
            db.session.add(match)
        
        # Save Free prediction
        free = predictions['free']
        free_prediction = Prediction(
            prediction_type='free',
            total_odds=free['total_odds'],
            success_probability=free['success_probability'],
            status='pending'
        )
        db.session.add(free_prediction)
        db.session.flush()
        
        # Add Free matches
        for match_data in free['matches']:
            match = Match(
                prediction_id=free_prediction.id,
                team_home=match_data['home_team'],
                team_away=match_data['away_team'],
                league=match_data['league'],
                match_time=datetime.fromisoformat(match_data['match_time'].replace('Z', '+00:00')),
                bet_type=match_data['bet_type'],
                odds=match_data['odds']
            )
            db.session.add(match)
        
        db.session.commit()
        print(f"✅ Saved predictions: VIP #{vip_prediction.id}, Free #{free_prediction.id}")


if __name__ == '__main__':
    # Test prediction generation
    generator = PredictionGenerator()
    predictions = generator.generate_predictions()
    
    if predictions:
        print("\n=== VIP PREDICTION ===")
        print(f"Total Odds: {predictions['vip']['total_odds']}")
        print(f"Success Probability: {predictions['vip']['success_probability']*100:.1f}%")
        for m in predictions['vip']['matches']:
            print(f"  • {m['home_team']} vs {m['away_team']} | {m['bet_type']} @ {m['odds']}")
        
        print("\n=== FREE PREDICTION ===")
        print(f"Total Odds: {predictions['free']['total_odds']}")
        print(f"Success Probability: {predictions['free']['success_probability']*100:.1f}%")
        for m in predictions['free']['matches']:
            print(f"  • {m['home_team']} vs {m['away_team']} | {m['bet_type']} @ {m['odds']}")
