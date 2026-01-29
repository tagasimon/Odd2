"""
Odd 2 - AI Prediction Analyzer
Analyzes match data to predict goal probabilities using multiple factors
"""
import math
from datetime import datetime


class MatchAnalyzer:
    """
    AI model for predicting goal probabilities in football matches.
    Uses multiple factors: form, H2H, league position, goal averages, etc.
    """
    
    def __init__(self, data_fetcher):
        """
        Initialize analyzer with a data fetcher
        
        Args:
            data_fetcher: FootballDataFetcher instance
        """
        self.fetcher = data_fetcher
        
        # Weights for different factors in probability calculation
        self.weights = {
            'team_scoring_form': 0.25,
            'team_conceding_form': 0.20,
            'h2h_history': 0.15,
            'league_position': 0.10,
            'home_advantage': 0.10,
            'recent_goals_trend': 0.20
        }
        
        # Base probabilities for different over thresholds (from historical data)
        self.base_probabilities = {
            0.5: 0.92,   # Over 0.5 goals
            1.5: 0.72,   # Over 1.5 goals
            2.5: 0.52,   # Over 2.5 goals
            3.5: 0.32,   # Over 3.5 goals
            4.5: 0.18,   # Over 4.5 goals
        }
    
    def analyze_match(self, match_data):
        """
        Analyze a match and predict goal probabilities
        
        Args:
            match_data: dict with home_team, away_team, competition, etc.
            
        Returns:
            dict with probabilities for different over thresholds
        """
        home_team_id = match_data.get('home_team_id')
        away_team_id = match_data.get('away_team_id')
        match_id = match_data.get('id')
        
        # Get team data
        home_matches = self.fetcher.get_team_matches(home_team_id, limit=10) if home_team_id else []
        away_matches = self.fetcher.get_team_matches(away_team_id, limit=10) if away_team_id else []
        
        # Get H2H if available
        h2h = self.fetcher.get_head_to_head(match_id) if match_id else {'avg_goals': 2.5}
        
        # Calculate factors
        factors = self._calculate_factors(home_matches, away_matches, h2h)
        
        # Predict probabilities for each threshold
        predictions = {}
        for threshold, base_prob in self.base_probabilities.items():
            adjusted_prob = self._adjust_probability(base_prob, factors, threshold)
            predictions[threshold] = {
                'probability': min(0.95, max(0.05, adjusted_prob)),  # Clamp between 5-95%
                'bet_type': f'Over {threshold}',
                'confidence': self._calculate_confidence(factors)
            }
        
        return predictions
    
    def _calculate_factors(self, home_matches, away_matches, h2h):
        """
        Calculate all analysis factors from match data
        
        Returns:
            dict with factor values (-1 to +1 range, 0 = neutral)
        """
        factors = {
            'team_scoring_form': 0,
            'team_conceding_form': 0,
            'h2h_history': 0,
            'league_position': 0,
            'home_advantage': 0.1,  # Default home advantage
            'recent_goals_trend': 0
        }
        
        # Team scoring form (how many goals teams score)
        if home_matches:
            home_avg_scored = sum(m['goals_for'] for m in home_matches) / len(home_matches)
            factors['team_scoring_form'] += (home_avg_scored - 1.3) / 2  # Normalize around average
        
        if away_matches:
            away_avg_scored = sum(m['goals_for'] for m in away_matches) / len(away_matches)
            factors['team_scoring_form'] += (away_avg_scored - 1.3) / 2
        
        # Team conceding form (how many goals teams concede)
        if home_matches:
            home_avg_conceded = sum(m['goals_against'] for m in home_matches) / len(home_matches)
            factors['team_conceding_form'] += (home_avg_conceded - 1.3) / 2
        
        if away_matches:
            away_avg_conceded = sum(m['goals_against'] for m in away_matches) / len(away_matches)
            factors['team_conceding_form'] += (away_avg_conceded - 1.3) / 2
        
        # H2H history
        h2h_avg = h2h.get('avg_goals', 2.5)
        factors['h2h_history'] = (h2h_avg - 2.5) / 3  # Normalize
        
        # Recent goals trend (averaging total goals in recent matches)
        all_matches = home_matches[:5] + away_matches[:5]
        if all_matches:
            avg_total = sum(m['total_goals'] for m in all_matches) / len(all_matches)
            factors['recent_goals_trend'] = (avg_total - 2.5) / 2
        
        # Clamp all factors to reasonable range
        for key in factors:
            factors[key] = max(-0.5, min(0.5, factors[key]))
        
        return factors
    
    def _adjust_probability(self, base_prob, factors, threshold):
        """
        Adjust base probability based on calculated factors
        
        Args:
            base_prob: Base probability for this threshold
            factors: Calculated factor values
            threshold: Goal threshold (1.5, 2.5, etc.)
            
        Returns:
            Adjusted probability (0.0 to 1.0)
        """
        # Calculate weighted adjustment
        adjustment = sum(
            factors.get(factor, 0) * weight
            for factor, weight in self.weights.items()
        )
        
        # Apply adjustment (higher factors = more goals likely)
        adjusted = base_prob + adjustment
        
        # Additional threshold-specific adjustments
        # Lower thresholds are more affected by scoring form
        if threshold <= 1.5:
            adjusted += factors['team_scoring_form'] * 0.1
        # Higher thresholds need strong signals
        elif threshold >= 3.5:
            adjusted += factors['recent_goals_trend'] * 0.15
        
        return adjusted
    
    def _calculate_confidence(self, factors):
        """
        Calculate confidence level in the prediction
        
        Returns:
            'high', 'medium', or 'low'
        """
        # Check for strong signals (large factor values)
        strong_signals = sum(1 for v in factors.values() if abs(v) > 0.2)
        
        if strong_signals >= 3:
            return 'high'
        elif strong_signals >= 1:
            return 'medium'
        else:
            return 'low'
    
    def get_best_bet_type(self, predictions, min_prob=0.55):
        """
        Determine the best "over" bet type for a match
        
        Args:
            predictions: dict of threshold -> prediction data
            min_prob: Minimum probability to consider
            
        Returns:
            Best bet type (e.g., 'Over 2.5') or None if no good options
        """
        # Priority order: Over 2.5 > Over 1.5 > Over 3.5 > Over 0.5
        priority_order = [2.5, 1.5, 3.5, 0.5, 4.5]
        
        for threshold in priority_order:
            if threshold in predictions:
                pred = predictions[threshold]
                if pred['probability'] >= min_prob:
                    return {
                        'bet_type': pred['bet_type'],
                        'probability': pred['probability'],
                        'threshold': threshold
                    }
        
        # Return highest probability bet if none meet threshold
        best = max(predictions.items(), key=lambda x: x[1]['probability'])
        return {
            'bet_type': best[1]['bet_type'],
            'probability': best[1]['probability'],
            'threshold': best[0]
        }
    
    def calculate_combined_probability(self, bets):
        """
        Calculate combined probability for multiple bets
        (All must win for the combination to win)
        
        Args:
            bets: List of dicts with 'probability' key
            
        Returns:
            Combined probability (0.0 to 1.0)
        """
        if not bets:
            return 0.0
        
        combined = 1.0
        for bet in bets:
            combined *= bet.get('probability', 0.5)
        
        return combined
    
    def calculate_combined_odds(self, bets):
        """
        Calculate combined odds for multiple bets
        
        Args:
            bets: List of dicts with 'odds' key
            
        Returns:
            Combined odds (product of all odds)
        """
        if not bets:
            return 0.0
        
        combined = 1.0
        for bet in bets:
            combined *= bet.get('odds', 1.0)
        
        return round(combined, 2)


class OddsEstimator:
    """
    Estimates realistic odds for over goals markets
    Based on probability and typical bookmaker margins
    """
    
    BOOKMAKER_MARGIN = 0.05  # 5% margin typical
    
    @classmethod
    def probability_to_odds(cls, probability):
        """
        Convert probability to decimal odds with bookmaker margin
        
        Args:
            probability: 0.0 to 1.0
            
        Returns:
            Decimal odds (e.g., 1.80, 2.10)
        """
        if probability <= 0 or probability >= 1:
            return 1.01
        
        # Fair odds
        fair_odds = 1 / probability
        
        # Apply margin (reduce odds slightly)
        adjusted_odds = fair_odds * (1 - cls.BOOKMAKER_MARGIN)
        
        return round(max(1.01, adjusted_odds), 2)
    
    @classmethod
    def estimate_over_odds(cls, threshold, probability):
        """
        Estimate odds for an over goals market
        
        Args:
            threshold: Goal threshold (1.5, 2.5, etc.)
            probability: Predicted probability
            
        Returns:
            Estimated decimal odds
        """
        # Typical odds ranges for different thresholds
        typical_ranges = {
            0.5: (1.01, 1.15),
            1.5: (1.10, 1.70),
            2.5: (1.40, 2.40),
            3.5: (1.80, 3.50),
            4.5: (2.50, 5.00)
        }
        
        odds = cls.probability_to_odds(probability)
        
        # Clamp to typical range for this threshold
        if threshold in typical_ranges:
            min_odds, max_odds = typical_ranges[threshold]
            odds = max(min_odds, min(max_odds, odds))
        
        return odds
