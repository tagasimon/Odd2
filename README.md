# Odd 2 - Football Predictions Website

AI-powered football predictions website focusing on "over goals" bets with odds of 2.0+ to help users double their money.

## Features

- 🤖 AI-powered prediction engine analyzing team statistics
- ⚽ Focus on "over goals" bets (Over 1.5, 2.5, 3.5)
- 💰 VIP predictions with highest success probability
- 📊 7-day history with color-coded results
- 💳 Mobile money payments via Relworx
- 🌍 Multi-currency support (UGX, KES, TZS, RWF)
- ⏰ Automated updates at 12 PM & 12 AM EAT

## Quick Start

### 1. Clone and Setup
```bash
cd /Users/kazoobasimon/PycharmProjects/Odd2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Initialize Database
```bash
python -c "from database.init_db import init_database; init_database()"
```

### 4. Run Development Server
```bash
python app.py
```

Visit http://127.0.0.1:5000

## API Keys Required

1. **Football-Data.org** (free tier): https://www.football-data.org/
2. **Relworx Payment API**: https://payments.relworx.com/docs/

## Project Structure

```
Odd2/
├── app.py                  # Main Flask application
├── config.py               # Configuration settings
├── database/               # Database models & initialization
├── prediction/             # AI prediction engine
├── payment/                # Relworx payment integration
├── utils/                  # Helper utilities
├── templates/              # HTML templates
└── static/                 # CSS, JS, images
```

## Scheduled Tasks

| Time | Task |
|------|------|
| 12:00 PM EAT | Generate new predictions |
| 12:00 AM EAT | Generate new predictions |
| Hourly | Update match results |
| Daily | Refresh currency rates |

## License

MIT License
