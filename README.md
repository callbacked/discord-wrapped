# Discord Wrapped

Discord Wrapped is a bot that generates personalized activity summaries for Discord users, similar to Spotify Wrapped. It analyzes user activity and creates beautiful visualizations of their Discord usage patterns.

- Web dashboard for viewing statistics and customizable cards
- Customizable personality traits
- Can support multiple servers with its own individual settings

![main](https://raw.githubusercontent.com/callbacked/discord-wrapped/refs/heads/main/screenshots/showcase.png)
![cards](https://github.com/callbacked/discord-wrapped/blob/main/screenshots/cards_showcase.png?raw=true)
![summary](https://github.com/callbacked/discord-wrapped/blob/main/screenshots/summary_card.png?raw=true)

## Prerequisites

- Docker and Docker Compose (for Docker deployment)
- Python 3.8 or higher (for local development)
- A Discord Bot Token (see [Setup](#setup))

## Setup

1. Create a Discord Application and Bot:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the Bot section and create a bot
   - Save the bot token
   - Under OAuth2 → General, note your Client ID and Client Secret
   - Set up your redirect URI (e.g., `http://localhost:5001/callback`)

2. Configure the bot (choose one method):

   ### Option A: Using Environment Variables (Local Setup)
   Create a `.env` file with:
   ```
   DISCORD_TOKEN=your_bot_token
   ADMIN_IDS=comma_separated_admin_ids
   CLIENT_ID=your_client_id
   CLIENT_SECRET=your_client_secret
   REDIRECT_URI=your_redirect_uri
   ```

   ### Option B: Using Docker Compose
   Edit `docker-compose.yml` and fill in your values:
   ```yaml
   environment:
     - DISCORD_TOKEN=your_bot_token
     - ADMIN_IDS=comma_separated_admin_ids
     - CLIENT_ID=your_client_id
     - CLIENT_SECRET=your_client_secret
     - REDIRECT_URI=your_redirect_uri
   ```

3. Start the bot:

   ### For Local Setup:
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the bot
   python main.py
   ```

   ### For Docker Setup:
   ```bash
   docker-compose up -d
   ```

## Project Structure

- `bot.py` - Main Discord bot logic
- `commands.py` - Bot command implementations
- `dashboard.py` - Web dashboard implementation
- `database.py` - Database operations
- `image_generator.py` - Statistics card generation
- `templates/` - Web dashboard templates
- `static/` - Static assets for the dashboard
- `resources/` - Fonts and other resources


## License

This project is licensed under the MIT License (do what you want honestly)

## Disclaimer

This is a self-hosted bot. You are responsible for:
- Hosting and maintaining your own instance
- Securing your bot token and other credentials
- Complying with Discord's Terms of Service and Developer Terms