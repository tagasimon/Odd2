"""
Odd 2 - Football Data Fetcher
Fetches match data, odds, and statistics from Football-Data.org API
"""
import requests
from datetime import datetime, timedelta
from config import Config


class FootballDataFetcher:
    """
    Fetches football data from Football-Data.org API
    Free tier includes: Premier League, Bundesliga, La Liga, Serie A, Ligue 1, Champions League
    """
    
    def __init__(self):
        self.api_key = Config.FOOTBALL_API_KEY
        self.base_url = Config.FOOTBALL_API_BASE_URL
        self.headers = {
            'X-Auth-Token': self.api_key
        }
        
        # Competition IDs for Free Tier
        self.competitions = {
            'PL': 'Premier League',
            'BL1': 'Bundesliga',
            'PD': 'La Liga',
            'SA': 'Serie A',
            'FL1': 'Ligue 1',
            'CL': 'Champions League',
            'EC': 'European Championship'
        }
    
    def _make_request(self, endpoint):
        """Make API request with error handling"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print("API rate limit exceeded")
                return None
            else:
                print(f"API error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    def get_upcoming_matches(self, days=0):
        """
        Get upcoming matches for today (or next N days if specified)
        
        Args:
            days: Number of days to look ahead (0 = today only)
            
        Returns:
            List of match dictionaries
        """
        # Date range for matches - default to today only
        date_from = datetime.now().strftime('%Y-%m-%d')
        date_to = (datetime.now() + timedelta(days=max(0, days))).strftime('%Y-%m-%d')
        
        matches = []
        
        for comp_id in self.competitions.keys():
            endpoint = f"/competitions/{comp_id}/matches?dateFrom={date_from}&dateTo={date_to}&status=SCHEDULED"
            data = self._make_request(endpoint)
            
            if data and 'matches' in data:
                for match in data['matches']:
                    matches.append({
                        'id': match['id'],
                        'competition': {
                            'id': comp_id,
                            'name': self.competitions.get(comp_id, comp_id)
                        },
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'home_team_id': match['homeTeam']['id'],
                        'away_team_id': match['awayTeam']['id'],
                        'match_time': match['utcDate']
                    })
        
        return matches
    
    def get_team_stats(self, team_id, competition_id):
        """
        Get team statistics for a competition
        
        Returns:
            dict with goals scored, conceded, form, etc.
        """
        endpoint = f"/teams/{team_id}"
        data = self._make_request(endpoint)
        
        if not data:
            return self._get_default_stats()
        
        # Basic team info
        stats = {
            'team_id': team_id,
            'team_name': data.get('name', 'Unknown'),
            'goals_scored_avg': 1.5,  # Will be calculated from matches
            'goals_conceded_avg': 1.2,
            'form': []  # Last 5 results
        }
        
        return stats
    
    def get_team_matches(self, team_id, limit=10):
        """
        Get recent matches for a team to calculate form
        
        Args:
            team_id: Football-Data team ID
            limit: Number of recent matches
            
        Returns:
            List of match results
        """
        endpoint = f"/teams/{team_id}/matches?status=FINISHED&limit={limit}"
        data = self._make_request(endpoint)
        
        if not data or 'matches' not in data:
            return []
        
        results = []
        for match in data['matches'][:limit]:
            home_score = match['score']['fullTime']['home'] or 0
            away_score = match['score']['fullTime']['away'] or 0
            total_goals = home_score + away_score
            
            is_home = match['homeTeam']['id'] == team_id
            
            if is_home:
                if home_score > away_score:
                    result = 'W'
                elif home_score < away_score:
                    result = 'L'
                else:
                    result = 'D'
                goals_for = home_score
                goals_against = away_score
            else:
                if away_score > home_score:
                    result = 'W'
                elif away_score < home_score:
                    result = 'L'
                else:
                    result = 'D'
                goals_for = away_score
                goals_against = home_score
            
            results.append({
                'match_id': match['id'],
                'date': match['utcDate'],
                'is_home': is_home,
                'goals_for': goals_for,
                'goals_against': goals_against,
                'total_goals': total_goals,
                'result': result
            })
        
        return results
    
    def get_head_to_head(self, match_id):
        """
        Get head-to-head stats for a match
        
        Args:
            match_id: Match ID
            
        Returns:
            H2H statistics
        """
        endpoint = f"/matches/{match_id}/head2head"
        data = self._make_request(endpoint)
        
        if not data:
            return {'avg_goals': 2.5, 'matches': 0}
        
        aggregates = data.get('aggregates', {})
        h2h_matches = data.get('matches', [])
        
        # Calculate average goals in H2H
        if h2h_matches:
            total_goals = sum(
                (m['score']['fullTime']['home'] or 0) + (m['score']['fullTime']['away'] or 0)
                for m in h2h_matches
                if m.get('score', {}).get('fullTime', {})
            )
            avg_goals = total_goals / len(h2h_matches) if h2h_matches else 2.5
        else:
            avg_goals = 2.5
        
        return {
            'avg_goals': avg_goals,
            'matches': len(h2h_matches),
            'home_wins': aggregates.get('homeTeam', {}).get('wins', 0),
            'away_wins': aggregates.get('awayTeam', {}).get('wins', 0),
            'draws': aggregates.get('homeTeam', {}).get('draws', 0)
        }
    
    def get_standings(self, competition_id):
        """
        Get league standings
        
        Returns:
            List of teams with position, points, goals
        """
        endpoint = f"/competitions/{competition_id}/standings"
        data = self._make_request(endpoint)
        
        if not data or 'standings' not in data:
            return []
        
        standings = []
        for standing in data['standings']:
            if standing['type'] == 'TOTAL':
                for team in standing['table']:
                    standings.append({
                        'team_id': team['team']['id'],
                        'team_name': team['team']['name'],
                        'position': team['position'],
                        'points': team['points'],
                        'played': team['playedGames'],
                        'won': team['won'],
                        'draw': team['draw'],
                        'lost': team['lost'],
                        'goals_for': team['goalsFor'],
                        'goals_against': team['goalsAgainst'],
                        'goal_diff': team['goalDifference']
                    })
        
        return standings
    
    def get_match_result(self, match_id):
        """
        Get the result of a completed match
        
        Returns:
            dict with scores or None if match not completed
        """
        endpoint = f"/matches/{match_id}"
        data = self._make_request(endpoint)
        
        if not data:
            return None
        
        if data.get('status') != 'FINISHED':
            return None
        
        score = data.get('score', {}).get('fullTime', {})
        home_goals = score.get('home', 0) or 0
        away_goals = score.get('away', 0) or 0
        
        return {
            'match_id': match_id,
            'home_goals': home_goals,
            'away_goals': away_goals,
            'total_goals': home_goals + away_goals,
            'status': 'FINISHED'
        }
    
    def _get_default_stats(self):
        """Return default stats when API fails"""
        return {
            'goals_scored_avg': 1.5,
            'goals_conceded_avg': 1.2,
            'form': ['W', 'D', 'W', 'L', 'W'],
            'home_advantage': 1.1
        }


def test_api_connection():
    """Test the Football Data API connection"""
    fetcher = FootballDataFetcher()
    
    if not fetcher.api_key:
        print("⚠️  No API key configured. Set FOOTBALL_API_KEY in .env")
        return False
    
    # Try to fetch upcoming matches
    matches = fetcher.get_upcoming_matches(days=1)
    
    if matches:
        print(f"✅ API connection successful! Found {len(matches)} upcoming matches")
        return True
    else:
        print("⚠️  API connection may have issues or no matches found")
        return False


if __name__ == '__main__':
    test_api_connection()
