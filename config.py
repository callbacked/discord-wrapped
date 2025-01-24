import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.ENV = os.environ.get('BOT_ENV', 'development')
        self.DEBUG = self.ENV == 'development'
        self.DATABASE_PATH = "user_activity.db" if self.DEBUG else "database.db"
        self.ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        
        self.CLIENT_ID = os.getenv('CLIENT_ID')
        self.CLIENT_SECRET = os.getenv('CLIENT_SECRET')
        self.REDIRECT_URI = os.getenv('REDIRECT_URI')
        
        self.PRIMARY_TRAITS = {
            "The Yapper": {
                "message_ratio": 1.5,
                "message_threshold": 5000,
                "description": "Sends 150% more messages than server average (e.g., if server average is 1000 messages/year, they send 2500+) and has sent over 5,000 messages total"
            },
            "The Reactor": {
                "reaction_threshold": 1000,
                "description": "Has given or received over 1,000 reactions total (avg. 2-3 reactions per day over a year)"
            },
            "Touch Grass": {
                "voice_ratio": 1.5,
                "voice_threshold": 1000,
                "description": "Spends 150% more time in voice than server average (e.g., if average is 500 mins/year, they spend 1250+ mins) and has spent over 1,000 minutes in voice"
            },
            "The Performer": {
                "stream_threshold": 300,
                "description": "Has streamed content for over 300 minutes total (avg. 25 minutes per month over a year)"
            },
            "The Lone Wolf": {
                "deafen_ratio": 0.8,
                "voice_threshold": 500,
                "description": "Spends 80% of their voice time deafened (e.g., 400+ mins deafened out of 500 mins in voice) and has spent over 500 minutes in voice"
            },
            "The Lurker": {
                "message_ratio": 0.2,
                "voice_ratio": 0.2,
                "description": "Messages and voice time are 80% below server average (e.g., if yearly average is 1000 messages and 500 mins, they have 200 or fewer messages and 100 or fewer mins)"
            },
            "The Ghost": {
                "message_threshold": 100,
                "voice_threshold": 60,
                "description": "Minimal activity with fewer than 100 messages sent (avg. 8 per month) and less than 60 minutes in voice channels (5 mins per month)"
            },
            "The Silent Observer": {
                "message_threshold": 300,
                "voice_threshold": 120,
                "description": "Light participation with under 300 messages sent (avg. 25 per month) and less than 120 minutes in voice channels (10 mins per month)"
            },
            "The Reactive": {
                "message_threshold": 1000,
                "reaction_threshold": 800,
                "description": "Balanced engagement with over 1,000 messages sent (avg. 83 per month) and over 800 reactions given or received"
            },
            "The Voice Only": {
                "message_threshold": 300,
                "voice_threshold": 600,
                "description": "Prefers voice with under 300 messages (avg. 25 per month) but over 600 minutes in voice channels (50 mins per month)"
            },
            "The Deafen Master": {
                "deafen_ratio": 0.9,
                "deafen_threshold": 1200,
                "description": "Spends 90% of voice time deafened (e.g., 1080+ mins deafened out of 1200 mins in voice) and has spent over 1,200 minutes in voice"
            },
            "The Stream Sniper": {
                "stream_threshold": 120,
                "voice_threshold": 500,
                "description": "Over 120 minutes streaming (10 mins per month) while spending more than 500 minutes in voice channels"
            }
        }
        
        self.SECONDARY_TRAITS = {
            "Chatty": {
                "message_threshold": 3000,
                "description": "High volume texter with over 3,000 messages sent (avg. 250+ messages per month)"
            },
            "Regular Chatter": {
                "message_threshold": 1200,
                "description": "Consistent texter with over 1,200 messages sent (avg. 100+ messages per month)"
            },
            "Casual Chatter": {
                "message_threshold": 360,
                "description": "Occasional texter with over 360 messages sent (avg. 30+ messages per month)"
            },
            "Occasional Speaker": {
                "message_threshold": 12,
                "description": "Has sent at least one message per month on average"
            },
            "Very Expressive": {
                "reaction_threshold": 1000,
                "description": "Heavy reaction user with over 1,000 reactions (given or received, avg. 83+ per month)"
            },
            "Reactive": {
                "reaction_threshold": 400,
                "description": "Regular reaction user with over 400 reactions (given or received, avg. 33+ per month)"
            },
            "Reserved": {
                "reaction_threshold": 120,
                "description": "Light reaction user with over 120 reactions (given or received, avg. 10+ per month)"
            },
            "Very Social": {
                "voice_threshold": 720,
                "description": "Frequent voice user with over 720 minutes in voice (avg. 60+ minutes per month)"
            },
            "Social": {
                "voice_threshold": 360,
                "description": "Regular voice user with over 360 minutes in voice (avg. 30+ minutes per month)"
            },
            "Occasional Visitor": {
                "voice_threshold": 120,
                "description": "Light voice user with over 120 minutes in voice channels (avg. 10+ minutes per month)"
            },
            "Content Creator": {
                "stream_threshold": 360,
                "description": "Dedicated streamer with over 360 minutes of stream time (avg. 30+ minutes per month)"
            },
            "Stream Enthusiast": {
                "stream_threshold": 180,
                "description": "Regular streamer with over 180 minutes of stream time (avg. 15+ minutes per month)"
            },
            "Casual Streamer": {
                "stream_threshold": 60,
                "description": "Occasional streamer with over 60 minutes of stream time (avg. 5+ minutes per month)"
            },
            "Solo Player": {
                "deafen_ratio": 0.8,
                "description": "Spends 80% of voice time deafened (e.g., 400+ mins deafened out of 500 mins in voice)"
            },
            "Sometimes Social": {
                "deafen_ratio": 0.5,
                "description": "Spends 50% of voice time deafened (e.g., 250 mins deafened out of 500 mins in voice)"
            },
            "Always Listening": {
                "deafen_ratio": 0.1,
                "description": "Rarely deafens, only 10% of voice time deafened (e.g., 50 mins deafened out of 500 mins in voice)"
            },
            "Wallflower": {
                "message_ratio": 0.1,
                "voice_ratio": 0.1,
                "description": "90% below server average in both messages and voice (e.g., if yearly average is 1000 messages and 500 mins, they have 100 or fewer messages and 50 or fewer mins)"
            },
            "Silent Type": {
                "message_ratio": 0.05,
                "description": "95% below server average in messages (e.g., if yearly average is 1000 messages, they have 50 or fewer)"
            }
        }
        
        print(f"CLIENT_ID: {self.CLIENT_ID}")
        print(f"CLIENT_SECRET: {self.CLIENT_SECRET}")
        print(f"REDIRECT_URI: {self.REDIRECT_URI}")
        
        if not self.TOKEN:
            raise ValueError("DISCORD_TOKEN environment variable is not set.")
        if not self.ADMIN_IDS:
            logging.warning("No ADMIN_IDS provided. Admin commands will not be available.")
        
        log_level = logging.DEBUG if self.DEBUG else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(f'discord_bot_{self.ENV}.log'),
                logging.StreamHandler()
            ]
        )
        logging.info(f'Initialized in {self.ENV.upper()} mode')