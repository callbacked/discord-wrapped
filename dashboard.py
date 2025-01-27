from flask import Flask, redirect, request, session, url_for, render_template, jsonify, send_file
import requests
import os
import logging
import sqlite3
from config import Config
from urllib.parse import quote
import io
import json
from image_generator import create_metric_card
import asyncio
from asgiref.sync import async_to_sync
from functools import wraps
from commands import COLOR_PALETTES

app = Flask(__name__)
app.secret_key = os.urandom(24)
config = Config()
logging.basicConfig(level=logging.DEBUG)  

REDIRECT_URI = config.REDIRECT_URI
CLIENT_ID = config.CLIENT_ID
CLIENT_SECRET = config.CLIENT_SECRET
BOT_TOKEN = config.TOKEN  

DISCORD_API_URL = 'https://discord.com/api'
AUTHORIZATION_BASE_URL = 'https://discord.com/oauth2/authorize'

def get_db():
    db = sqlite3.connect('user_activity.db')
    db.row_factory = sqlite3.Row
    return db

def async_route(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(f(*args, **kwargs))
    return wrapped

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        
        user_id = int(session['user']['id'])
        if user_id not in config.ADMIN_IDS:
            return render_template('error.html', 
                                 error="Unauthorized", 
                                 message="You don't have permission to access this page. Only bot administrators can access the dashboard.")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@admin_required
def index():
    if 'user' not in session:
        return redirect(url_for('login'))

    guilds_response = requests.get(
        f'{DISCORD_API_URL}/users/@me/guilds',
        headers={'Authorization': f'Bearer {session["access_token"]}'}
    )
    
    if guilds_response.status_code != 200:
        logging.error(f"Failed to fetch guilds: {guilds_response.status_code} - {guilds_response.text}")
        return "Failed to fetch your servers.", 400

    guilds = guilds_response.json()
    manageable_guilds = [
        guild for guild in guilds 
        if (guild['permissions'] & 0x8) == 0x8
    ]

    bot_guilds_response = requests.get(
        f'{DISCORD_API_URL}/users/@me/guilds',
        headers={'Authorization': f'Bot {BOT_TOKEN}'}
    )
    bot_guild_ids = []
    if bot_guilds_response.status_code == 200:
        bot_guild_ids = [g['id'] for g in bot_guilds_response.json()]

    for guild in manageable_guilds:
        guild['bot_present'] = guild['id'] in bot_guild_ids

    session['manageable_guilds'] = manageable_guilds
    if 'selected_guild_id' not in session:
        session['selected_guild_id'] = manageable_guilds[0]['id'] if manageable_guilds else None

    return render_template('dashboard.html', 
                         user=session['user'], 
                         guilds=manageable_guilds, 
                         selected_guild_id=session['selected_guild_id'],
                         bot_in_server=session['selected_guild_id'] in bot_guild_ids)

@app.route('/select_guild', methods=['POST'])
@admin_required
def select_guild():
    if 'user' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    guild_id = data.get('guild_id')
    
    if guild_id not in [guild['id'] for guild in session.get('manageable_guilds', [])]:
        return jsonify({"error": "Invalid guild ID"}), 400
        
    session['selected_guild_id'] = guild_id

    bot_guilds_response = requests.get(
        f'{DISCORD_API_URL}/users/@me/guilds',
        headers={'Authorization': f'Bot {BOT_TOKEN}'}
    )
    bot_in_server = False
    if bot_guilds_response.status_code == 200:
        bot_guild_ids = [g['id'] for g in bot_guilds_response.json()]
        bot_in_server = guild_id in bot_guild_ids

    return jsonify({
        "success": True,
        "bot_in_server": bot_in_server
    })

@app.route('/get_default_traits')
@admin_required
def get_default_traits():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    cursor = db.cursor()
    admin_id = session['user']['id']
    server_id = session['selected_guild_id']

    cursor.execute('''
        SELECT * FROM custom_traits 
        WHERE admin_id = ? AND server_id = ?
    ''', (admin_id, server_id))
    
    custom_traits = cursor.fetchall()
    custom_traits = [dict(trait) for trait in custom_traits]

    traits = {
        "primary": dict(config.PRIMARY_TRAITS),
        "secondary": dict(config.SECONDARY_TRAITS)
    }

    for trait in custom_traits:
        trait_type = trait['trait_type']
        original_name = trait['original_name']
        custom_name = trait['custom_name']
        
        if original_name in traits[trait_type]:
            del traits[trait_type][original_name]
        
        thresholds = {
            'message_ratio': trait['message_ratio'],
            'message_threshold': trait['message_threshold'],
            'reaction_threshold': trait['reaction_threshold'],
            'voice_ratio': trait['voice_ratio'],
            'voice_threshold': trait['voice_threshold'],
            'stream_threshold': trait['stream_threshold'],
            'deafen_ratio': trait['deafen_ratio'],
            'deafen_threshold': trait['deafen_threshold']
        }
        
        traits[trait_type][custom_name] = {
            **thresholds,
            'description': trait['description']
        }
    
    logging.info(f"Returning traits: {traits}")
    return jsonify(traits)

@app.route('/update_traits', methods=['POST'])
def update_traits():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    trait_type = data.get('trait_type')
    original_name = data.get('trait_name')
    custom_name = data.get('new_name')
    custom_description = data.get('description')  
    thresholds = data.get('thresholds', {})
    
    # Validate thresholds
    valid_thresholds = {
        'message_ratio': float,
        'message_threshold': int,
        'reaction_threshold': int,
        'voice_ratio': float,
        'voice_threshold': int,
        'stream_threshold': int,
        'deafen_ratio': float,
        'deafen_threshold': int
    }
    
    processed_thresholds = {}
    for key, value in thresholds.items():
        if key not in valid_thresholds:
            continue
            
        try:
            if value is not None:
                processed_thresholds[key] = valid_thresholds[key](value)
            else:
                processed_thresholds[key] = None
        except (ValueError, TypeError):
            return jsonify({"error": f"Invalid value for {key}"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            SELECT COUNT(*) FROM custom_traits 
            WHERE admin_id = ? AND server_id = ? AND trait_type = ? AND original_name = ?
        ''', (
            session['user']['id'],
            session['selected_guild_id'],
            trait_type,
            original_name
        ))
        
        exists = cursor.fetchone()[0] > 0
        
        description = custom_description  
        if not description: 
            if original_name in config.PRIMARY_TRAITS and trait_type == "primary":
                description = config.PRIMARY_TRAITS[original_name].get('description', traitDescriptions["primary"].get(original_name))
            elif original_name in config.SECONDARY_TRAITS and trait_type == "secondary":
                description = config.SECONDARY_TRAITS[original_name].get('description', traitDescriptions["secondary"].get(original_name))
            
            if not description:  
                description = "Custom trait"
        
        if exists:
            cursor.execute('''
                UPDATE custom_traits 
                SET custom_name = ?,
                    description = ?,
                    message_ratio = ?, message_threshold = ?, reaction_threshold = ?,
                    voice_ratio = ?, voice_threshold = ?, stream_threshold = ?,
                    deafen_ratio = ?, deafen_threshold = ?
                WHERE admin_id = ? AND server_id = ? AND trait_type = ? AND original_name = ?
            ''', (
                custom_name or original_name,
                description,
                processed_thresholds.get('message_ratio'),
                processed_thresholds.get('message_threshold'),
                processed_thresholds.get('reaction_threshold'),
                processed_thresholds.get('voice_ratio'),
                processed_thresholds.get('voice_threshold'),
                processed_thresholds.get('stream_threshold'),
                processed_thresholds.get('deafen_ratio'),
                processed_thresholds.get('deafen_threshold'),
                session['user']['id'],
                session['selected_guild_id'],
                trait_type,
                original_name
            ))
        else:
            cursor.execute('''
                INSERT INTO custom_traits (
                    admin_id, server_id, trait_type, original_name, custom_name,
                    description,
                    message_ratio, message_threshold, reaction_threshold,
                    voice_ratio, voice_threshold, stream_threshold,
                    deafen_ratio, deafen_threshold
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session['user']['id'],
                session['selected_guild_id'],
                trait_type,
                original_name,
                custom_name or original_name,
                description,
                processed_thresholds.get('message_ratio'),
                processed_thresholds.get('message_threshold'),
                processed_thresholds.get('reaction_threshold'),
                processed_thresholds.get('voice_ratio'),
                processed_thresholds.get('voice_threshold'),
                processed_thresholds.get('stream_threshold'),
                processed_thresholds.get('deafen_ratio'),
                processed_thresholds.get('deafen_threshold')
            ))
        
        db.commit()
        
        logging.info(f"Updated trait: admin_id={session['user']['id']}, server_id={session['selected_guild_id']}, "
                    f"trait_type={trait_type}, trait_name={original_name}, new_name={custom_name}, "
                    f"thresholds={processed_thresholds}")
        
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        logging.error(f"Error updating trait: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reset_traits', methods=['POST'])
@admin_required
def reset_traits():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            DELETE FROM custom_traits 
            WHERE admin_id = ? AND server_id = ?
        ''', (session['user']['id'], session['selected_guild_id']))
        
        db.commit()
        logging.info(f"Reset all traits for admin_id={session['user']['id']}, server_id={session['selected_guild_id']}")
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        logging.error(f"Error resetting traits: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/discord_login')
def discord_login():
    oauth_url = f'{AUTHORIZATION_BASE_URL}?client_id={CLIENT_ID}&redirect_uri={quote(REDIRECT_URI)}&response_type=code&scope=identify%20guilds'
    return redirect(oauth_url)

@app.route('/add_bot')
def add_bot():

    # READ_MESSAGES (1024) + READ_MESSAGE_HISTORY (65536) + ADD_REACTIONS (64) + 
    # VIEW_SERVER_INSIGHTS (524288) + CONNECT (1048576)
    permissions = 1639488  
    oauth_url = f'{AUTHORIZATION_BASE_URL}?client_id={CLIENT_ID}&scope=bot&permissions={permissions}'
    return redirect(oauth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return 'Error: No code provided', 400

    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify guilds'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(
        f'{DISCORD_API_URL}/oauth2/token',
        data=data,
        headers=headers
    )

    if response.status_code != 200:
        logging.error(f"Failed to obtain access token: {response.status_code} - {response.text}")
        return f"Error: Failed to obtain access token: {response.text}", 400

    access_token = response.json().get('access_token')
    session['access_token'] = access_token

    user_response = requests.get(
        f'{DISCORD_API_URL}/users/@me',
        headers={'Authorization': f'Bearer {access_token}'}
    )

    if user_response.status_code != 200:
        logging.error(f"Failed to fetch user data: {user_response.status_code} - {user_response.text}")
        return 'Error: Failed to fetch user data', 400

    user = user_response.json()
    session['user'] = user
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    session.pop('access_token', None)
    session.pop('selected_guild_id', None)
    session.pop('manageable_guilds', None)
    return redirect(url_for('index'))

@app.route('/get_server_stats')
@admin_required
def get_server_stats():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    guild_id = session['selected_guild_id']
    
    db = get_db()
    cursor = db.cursor()
    

    cursor.execute('''
        SELECT 
            COALESCE(SUM(messages_sent), 0) as total_messages,
            COALESCE(SUM(reactions_added), 0) as total_reactions,
            COALESCE(SUM(voice_time), 0) as total_voice_time,
            COALESCE(SUM(stream_time), 0) as total_stream_time,
            COALESCE(SUM(deafen_time), 0) as total_deafen_time,
            COUNT(*) as active_users
        FROM user_stats 
        WHERE opt_in_date IS NOT NULL
        AND guild_id = ?
    ''', (guild_id,))
    
    stats = dict(cursor.fetchone())
    
    cursor.execute('''
        SELECT 
            user_id,
            messages_sent,
            reactions_added,
            voice_time,
            stream_time,
            (
                -- Messages: 1 point each
                messages_sent + 
                -- Reactions: 0.5 points each
                (reactions_added * 0.5) + 
                -- Voice: 1 point per 5 minutes (12 points per hour)
                (voice_time / 300.0) +
                -- Stream: 2 points per 5 minutes (24 points per hour, bonus for streaming)
                (stream_time / 300.0 * 2)
            ) as activity_score
        FROM user_stats 
        WHERE opt_in_date IS NOT NULL
        AND guild_id = ?
        ORDER BY activity_score DESC
        LIMIT 5
    ''', (guild_id,))
    
    top_users = [dict(row) for row in cursor.fetchall()]
    
    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    for user in top_users:
        try:
            logging.info(f"Fetching data for user {user['user_id']}")
            user_response = requests.get(
                f'{DISCORD_API_URL}/users/{user["user_id"]}',
                headers=headers
            )
            logging.info(f"Response status: {user_response.status_code}")
            if user_response.status_code == 200:
                user_data = user_response.json()
                logging.info(f"User data received: {user_data}")
                user['username'] = f"{user_data['username']}#{user_data.get('discriminator', '0')}"
            else:
                logging.error(f"Failed to fetch user data: {user_response.text}")
                user['username'] = f'User {user["user_id"]}'
        except Exception as e:
            logging.error(f"Failed to fetch user data: {e}")
            user['username'] = f'User {user["user_id"]}'
    
    logging.info(f"Final top users data: {top_users}")
    
    cursor.execute('''
        SELECT 
            mention_type,
            mentioned_id,
            CASE 
                WHEN mention_type = 'role' THEN 
                    COALESCE((
                        SELECT name 
                        FROM roles 
                        WHERE id = mention_stats.mentioned_id
                        AND guild_id = mention_stats.guild_id
                    ), 'Unknown Role')
                ELSE mention_type
            END as display_name,
            SUM(mention_count) as total_mentions
        FROM mention_stats
        WHERE guild_id = ?
        GROUP BY mention_type, mentioned_id
        ORDER BY total_mentions DESC
        LIMIT 10
    ''', (guild_id,))
    
    mention_stats = [dict(row) for row in cursor.fetchall()]
    
    headers = {'Authorization': f'Bot {BOT_TOKEN}'}
    for mention in mention_stats:
        if mention['mention_type'] == 'user':
            try:
                logging.info(f"Fetching data for mentioned user {mention['mentioned_id']}")
                user_response = requests.get(
                    f'{DISCORD_API_URL}/users/{mention["mentioned_id"]}',
                    headers=headers
                )
                logging.info(f"Response status: {user_response.status_code}")
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    logging.info(f"User data received: {user_data}")
                    mention['display_name'] = f"{user_data['username']}#{user_data.get('discriminator', '0')}"
                else:
                    logging.error(f"Failed to fetch user data: {user_response.text}")
                    mention['display_name'] = f'User {mention["mentioned_id"]}'
            except Exception as e:
                logging.error(f"Failed to fetch user data: {e}")
                mention['display_name'] = f'User {mention["mentioned_id"]}'
    
    return jsonify({
        "overview": stats,
        "top_users": top_users,
        "mentions": mention_stats
    })

@app.route('/create_trait', methods=['POST'])
def create_trait():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.json
    trait_type = data.get('trait_type')
    trait_name = data.get('trait_name')
    description = data.get('description')
    thresholds = data.get('thresholds', {})
    
    valid_thresholds = {
        'message_ratio': float,
        'message_threshold': int,
        'reaction_threshold': int,
        'voice_ratio': float,
        'voice_threshold': int,
        'stream_threshold': int,
        'deafen_ratio': float,
        'deafen_threshold': int
    }
    
    processed_thresholds = {}
    for key, value in thresholds.items():
        if key not in valid_thresholds:
            continue
            
        try:
            if value is not None:
                processed_thresholds[key] = valid_thresholds[key](value)
            else:
                processed_thresholds[key] = None
        except (ValueError, TypeError):
            return jsonify({"error": f"Invalid value for {key}"}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO custom_traits (
                admin_id, server_id, trait_type, original_name, custom_name,
                description,
                message_ratio, message_threshold, reaction_threshold,
                voice_ratio, voice_threshold, stream_threshold,
                deafen_ratio, deafen_threshold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['user']['id'],
            session['selected_guild_id'],
            trait_type,
            trait_name,  # For new traits, original_name is the same as trait_name
            trait_name,  # custom_name starts as the same as trait_name
            description,
            processed_thresholds.get('message_ratio'),
            processed_thresholds.get('message_threshold'),
            processed_thresholds.get('reaction_threshold'),
            processed_thresholds.get('voice_ratio'),
            processed_thresholds.get('voice_threshold'),
            processed_thresholds.get('stream_threshold'),
            processed_thresholds.get('deafen_ratio'),
            processed_thresholds.get('deafen_threshold')
        ))
        
        db.commit()
        
        logging.info(f"Created trait: admin_id={session['user']['id']}, server_id={session['selected_guild_id']}, "
                    f"trait_type={trait_type}, trait_name={trait_name}, "
                    f"description={description}, thresholds={processed_thresholds}")
        
        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        logging.error(f"Error creating trait: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/preview-card', methods=['POST'])
@admin_required
@async_route
async def preview_card():
    try:
        settings = request.json
        app.logger.debug(f"Received preview request with settings: {settings}")
        
        background_color = None
        if settings.get('useIndividualColors'):
            stat_type = 'messages'  
            background_color = hex_to_rgb(settings['statColors'].get(stat_type))
        else:

            palette_name = settings.get('colorPalette', 'default')
            if palette_name in COLOR_PALETTES:
                stat_type = 'messages'  
                background_color = hex_to_rgb(COLOR_PALETTES[palette_name]['colors'][stat_type])
        
        app.logger.debug("Generating preview card...")
        preview_image = await create_metric_card(
            title="Sample Messages",
            value="1,234",
            background_color=background_color,
            text_color=hex_to_rgb(settings['textColor']),
            animation_speed=settings['animationSpeed'],
            wave_intensity=settings['waveIntensity'],
            card_style=settings['cardStyle'],
            font_size=settings['fontSize']
        )
        
        app.logger.debug("Preview card generated, preparing response...")
        
        if not preview_image or not hasattr(preview_image, 'fp'):
            app.logger.error("Preview image generation failed - no valid image data")
            raise ValueError("Failed to generate preview image")
        
        preview_image.fp.seek(0)
        img_data = preview_image.fp.read()
        
        if not img_data:
            app.logger.error("No image data in preview")
            raise ValueError("No image data in preview")
            
        import base64
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        
        app.logger.debug("Sending preview response...")
        return jsonify({
            'success': True,
            'preview_url': f'data:image/gif;base64,{img_base64}'
        })
    except Exception as e:
        app.logger.error(f"Error generating preview: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/apply-card-settings', methods=['POST'])
@admin_required
def apply_card_settings():
    try:
        if 'user' not in session or 'selected_guild_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
            
        settings = request.json
        user_id = session['user']['id']
        server_id = session['selected_guild_id']
        
        app.logger.debug(f"Applying card settings for user {user_id} in server {server_id}: {settings}")
        
        save_user_card_settings(
            user_id=user_id,
            server_id=server_id,
            settings={
                'colorPalette': settings.get('colorPalette', 'default'),
                'useIndividualColors': settings.get('useIndividualColors', False),
                'statColors': settings.get('statColors', {}),
                'textColor': settings.get('textColor', '#FFFFFF'),
                'animationSpeed': settings.get('animationSpeed', 1),
                'waveIntensity': settings.get('waveIntensity', 0.5),
                'cardStyle': settings.get('cardStyle', 'default'),
                'fontSize': settings.get('fontSize', 24)
            }
        )
        
        app.logger.debug("Card settings saved successfully")
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error applying settings: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-card-settings')
def get_card_settings():
    if 'user' not in session or 'selected_guild_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            SELECT settings FROM user_card_settings 
            WHERE user_id = ? AND server_id = ?
        ''', (session['user']['id'], session['selected_guild_id']))
        
        result = cursor.fetchone()
        if result:
            settings = json.loads(result[0])
            return jsonify(settings)
        else:

            return jsonify({
                'colorPalette': 'default',
                'useIndividualColors': False,
                'statColors': {},
                'textColor': '#FFFFFF',
                'animationSpeed': 1,
                'waveIntensity': 0.5,
                'cardStyle': 'default',
                'fontSize': 24
            })
    except Exception as e:
        app.logger.error(f"Error getting card settings: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    try:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except Exception as e:
        app.logger.error(f"Error converting hex color {hex_color}: {str(e)}")
        raise ValueError(f"Invalid hex color: {hex_color}")

def create_preview_card(background_color, text_color, animation_speed, wave_intensity, card_style, font_size):
    """Create a preview card with the given settings."""
    sample_data = {
        'title': 'Sample Stat',
        'value': '1,234'
    }
    
    return create_metric_card(
        title=sample_data['title'],
        value=sample_data['value'],
        background_color=background_color,
        text_color=text_color,
        animation_speed=animation_speed,
        wave_intensity=wave_intensity,
        card_style=card_style,
        font_size=font_size
    )

def save_user_card_settings(user_id, server_id, settings):
    """Save user's card settings to the database."""
    db = get_db()
    cursor = db.cursor()
    
    try:
        user_id = int(user_id)
        server_id = int(server_id)
        
        cursor.execute('''
            SELECT COUNT(*) FROM user_card_settings WHERE user_id = ? AND server_id = ?
        ''', (user_id, server_id))
        
        exists = cursor.fetchone()[0] > 0
        settings_json = json.dumps(settings)
        
        if exists:
            cursor.execute('''
                UPDATE user_card_settings
                SET settings = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND server_id = ?
            ''', (settings_json, user_id, server_id))
        else:
            cursor.execute('''
                INSERT INTO user_card_settings (user_id, server_id, settings, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (user_id, server_id, settings_json))
        
        db.commit()
        app.logger.debug(f"Saved card settings for user {user_id} in server {server_id}")
    except Exception as e:
        db.rollback()
        app.logger.error(f"Database error while saving card settings: {str(e)}")
        raise
    finally:
        cursor.close()