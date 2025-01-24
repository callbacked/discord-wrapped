from bot import ActivityBot
from config import Config
import threading
from dashboard import app

def run_bot():
    config = Config()
    client = ActivityBot()
    client.run(config.TOKEN)

def run_dashboard():
    app.run(host='0.0.0.0', port=5001)

def main():
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.start()
    
    run_bot()

if __name__ == "__main__":
    main()
