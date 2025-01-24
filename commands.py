import logging
import discord
from discord import app_commands
from datetime import datetime
from image_generator import create_metric_card, create_mentions_card, create_summary_card
import json

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    try:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except Exception as e:
        logging.error(f"Error converting hex color {hex_color}: {str(e)}")
        raise ValueError(f"Invalid hex color: {hex_color}")

class WrapCommands:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config

    def get_commands(self):
        return [
            app_commands.Command(
                name="optin",
                description="Opt in to yearly activity tracking",
                callback=self.optin
            ),
            app_commands.Command(
                name="wrap",
                description="Get your server activity wrap",
                callback=self.wrap
            ),
            app_commands.Command(
                name="allwrap",
                description="Debug: Get all users wrap statistics",
                callback=self.allwrap
            )
        ]

    async def optin(self, interaction: discord.Interaction):
        cursor = self.bot.db.cursor()
        cursor.execute('INSERT OR IGNORE INTO user_stats (user_id, guild_id, opt_in_date) VALUES (?, ?, ?)',
                      (interaction.user.id, interaction.guild_id, datetime.now().isoformat()))
        self.bot.db.commit()
        logging.info(f'User {interaction.user.display_name}({interaction.user.id}) opted in to tracking')
        await interaction.response.send_message("You've been opted in to activity tracking!", ephemeral=True)

    async def process_user_stats(self, user_stats, interaction=None, send_dm=False):
        try:
            user = await self.bot.fetch_user(user_stats['user_id'])
            cursor = self.bot.db.cursor()

            
            user_id = int(user_stats['user_id'])
            guild_id = int(user_stats['guild_id'])  
            
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                logging.error(f"Could not find guild with ID {guild_id}")
                return
            admin_id = guild.owner_id
            
            cursor.execute('SELECT settings FROM user_card_settings WHERE user_id = ? AND server_id = ?', (user_id, guild_id))
            card_settings_row = cursor.fetchone()
            card_settings = None
            if card_settings_row:
                try:
                    card_settings = json.loads(card_settings_row[0])
                    logging.info(f"Loaded card settings for user {user_id} in server {guild_id}: {card_settings}")
                except json.JSONDecodeError:
                    logging.error(f"Failed to parse card settings for user {user_id} in server {guild_id}")
            else:
                logging.info(f"No card settings found for user {user_id} in server {guild_id}")

            
            def get_card_settings(stat_type, for_summary=False):
                if not card_settings:
                    logging.debug(f"Using default settings for {stat_type} (no card settings found)")
                    return {}
                    
                if for_summary:
                    
                    settings = {}
                    if card_settings['useIndividualColors']:
                        
                        if 'messages' in card_settings['statColors']:  
                            settings['background_color'] = hex_to_rgb(card_settings['statColors']['messages'])
                            logging.debug(f"Using messages color for summary card: {card_settings['statColors']['messages']}")
                    else:
                        palette_name = card_settings['colorPalette']
                        if palette_name in COLOR_PALETTES and 'colors' in COLOR_PALETTES[palette_name]:
                            palette = COLOR_PALETTES[palette_name]
                            if 'messages' in palette['colors']:
                                settings['background_color'] = hex_to_rgb(palette['colors']['messages'])
                                logging.debug(f"Using color from palette {palette_name} for summary card: {palette['colors']['messages']}")
                    return settings
                else:
                    if card_settings['useIndividualColors']:
                        settings = {
                            'text_color': hex_to_rgb(card_settings['textColor']),
                            'animation_speed': float(card_settings['animationSpeed']),
                            'wave_intensity': float(card_settings['waveIntensity']),
                            'card_style': card_settings['cardStyle'],
                            'font_size': int(card_settings['fontSize'])
                        }
                        
                        if stat_type in card_settings['statColors']:
                            settings['background_color'] = hex_to_rgb(card_settings['statColors'][stat_type])
                            logging.debug(f"Using individual color for {stat_type}: {card_settings['statColors'][stat_type]}")
                    else:
                        palette_name = card_settings['colorPalette']
                        if palette_name in COLOR_PALETTES:
                            palette = COLOR_PALETTES[palette_name]
                            settings = {
                                'text_color': hex_to_rgb(card_settings['textColor']),  
                                'animation_speed': float(palette['animation_speed']),
                                'wave_intensity': float(palette['wave_intensity']),
                                'card_style': palette['card_style'],
                                'font_size': int(palette['font_size'])
                            }
                            
                            if 'colors' in palette and stat_type in palette['colors']:
                                settings['background_color'] = hex_to_rgb(palette['colors'][stat_type])
                                logging.debug(f"Using color from palette {palette_name} for {stat_type}: {palette['colors'][stat_type]}")
                        else:
                            settings = {
                                'text_color': hex_to_rgb(card_settings['textColor']),
                                'animation_speed': float(card_settings['animationSpeed']),
                                'wave_intensity': float(card_settings['waveIntensity']),
                                'card_style': card_settings['cardStyle'],
                                'font_size': int(card_settings['fontSize'])
                            }
                    
                    return settings

            voice_hours = round(user_stats['voice_time'] / 3600, 1)
            stream_hours = round(user_stats['stream_time'] / 3600, 1)
            deafen_hours = round(user_stats['deafen_time'] / 3600, 1)

            total_time = user_stats['voice_time'] + user_stats['stream_time'] + user_stats['deafen_time']
            message_ratio = user_stats['messages_sent'] / (user_stats['messages_sent'] + user_stats['reactions_added']) if (user_stats['messages_sent'] + user_stats['reactions_added']) > 0 else 0
            voice_ratio = user_stats['voice_time'] / total_time if total_time > 0 else 0
            deafen_ratio = user_stats['deafen_time'] / total_time if total_time > 0 else 0

            primary_traits = dict(self.config.PRIMARY_TRAITS)
            secondary_traits = dict(self.config.SECONDARY_TRAITS)

            server_id = user_stats['guild_id']
            
            logging.info(f"Fetching custom traits for admin_id={admin_id}, server_id={server_id}")
            
            cursor.execute('''
                SELECT * FROM custom_traits 
                WHERE admin_id = ? AND server_id = ?
            ''', (admin_id, server_id))
            
            custom_traits = cursor.fetchall()
            custom_traits = [dict(trait) for trait in custom_traits]
            
            logging.info(f"Fetched Custom Traits: {custom_traits}")

            for trait in custom_traits:
                trait_type = trait['trait_type']
                original_name = trait['original_name']
                custom_name = trait['custom_name']
                
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
                
                if trait_type == 'primary':
                    if original_name in primary_traits:
                        del primary_traits[original_name]
                    primary_traits[custom_name] = thresholds
                else:  
                    if original_name in secondary_traits:
                        del secondary_traits[original_name]
                    secondary_traits[custom_name] = thresholds

            logging.info(f"Merged Primary Traits: {primary_traits}")
            logging.info(f"Merged Secondary Traits: {secondary_traits}")

            primary_trait = "The Balanced One"
            for trait, conditions in primary_traits.items():
                conditions_met = True
                for key, threshold in conditions.items():
                    if threshold is None:
                        continue
                        
                    value = None
                    if key == "message_ratio":
                        value = message_ratio
                    elif key == "message_threshold":
                        value = user_stats['messages_sent']
                    elif key == "reaction_threshold":
                        value = user_stats['reactions_added']
                    elif key == "voice_ratio":
                        value = voice_ratio
                    elif key == "voice_threshold":
                        value = voice_hours
                    elif key == "stream_threshold":
                        value = stream_hours
                    elif key == "deafen_ratio":
                        value = deafen_ratio
                    elif key == "deafen_threshold":
                        value = deafen_hours
                        
                    if value is not None and value <= threshold:
                        conditions_met = False
                        break
                        
                if conditions_met:
                    primary_trait = trait
                    break

            secondary_traits_list = []
            for trait, conditions in secondary_traits.items():
                conditions_met = True
                for key, threshold in conditions.items():
                    if threshold is None:
                        continue
                        
                    value = None
                    if key == "message_ratio":
                        value = message_ratio
                    elif key == "message_threshold":
                        value = user_stats['messages_sent']
                    elif key == "reaction_threshold":
                        value = user_stats['reactions_added']
                    elif key == "voice_ratio":
                        value = voice_ratio
                    elif key == "voice_threshold":
                        value = voice_hours
                    elif key == "stream_threshold":
                        value = stream_hours
                    elif key == "deafen_ratio":
                        value = deafen_ratio
                    elif key == "deafen_threshold":
                        value = deafen_hours
                        
                    if value is not None and value <= threshold:
                        conditions_met = False
                        break
                        
                if conditions_met:
                    secondary_traits_list.append(trait)

            logging.info(f"Selected Primary Trait: {primary_trait}")
            logging.info(f"Selected Secondary Traits: {secondary_traits_list}")

            async def send_card(card, recipient, message=None):
                if send_dm:
                    if message:
                        await recipient.send(message)
                    await recipient.send(file=card)
                else:
                    await interaction.followup.send(file=card)

            if send_dm:
                await user.send("🎉 **Your Server Wrapped**")
                await user.send("Let's see what you've been up to this year...")
            else:
                await interaction.followup.send(f"🎉 **Stats for {user.name} ({user.id})**")

            messages_card = await create_metric_card(
                "Messages Sent", 
                f"{user_stats['messages_sent']:,}",
                **get_card_settings('messages')
            )
            await send_card(messages_card, user)

            reactions_card = await create_metric_card(
                "Reactions Added", 
                f"{user_stats['reactions_added']:,}",
                **get_card_settings('reactions')
            )
            await send_card(reactions_card, user)

            voice_card = await create_metric_card(
                "Voice Time", 
                f"{voice_hours:,} hours",
                **get_card_settings('voice')
            )
            await send_card(voice_card, user)

            stream_card = await create_metric_card(
                "Stream Time", 
                f"{stream_hours:,} hours",
                **get_card_settings('stream')
            )
            await send_card(stream_card, user)

            deafen_card = await create_metric_card(
                "Deafen Time", 
                f"{deafen_hours:,} hours",
                **get_card_settings('deafen')
            )
            await send_card(deafen_card, user)

            cursor.execute('''
                SELECT mentioned_id, mention_count 
                FROM mention_stats 
                WHERE user_id = ? AND mention_type = 'user' AND guild_id = ?
                ORDER BY mention_count DESC LIMIT 5
            ''', (user_stats['user_id'], user_stats['guild_id']))
            top_users = cursor.fetchall()

            if top_users:
                try:
                    async def fetch_user_avatar(user_id):
                        try:
                            user = await self.bot.fetch_user(user_id)
                            avatar_data = await user.display_avatar.read()
                            return avatar_data
                        except Exception as e:
                            logging.error(f"Failed to fetch avatar for user {user_id}: {e}")
                            return None

                    mentions_card = await create_mentions_card(
                        "Most Mentioned Users",
                        top_users,
                        fetch_user_avatar,
                        resolve_name=self.bot.fetch_user,
                        **get_card_settings('mentions')  
                    )
                    await send_card(mentions_card, user)
                except Exception as e:
                    logging.error(f"Failed to create mentions card: {e}")

            cursor.execute('''
                SELECT mentioned_id, mention_count 
                FROM mention_stats 
                WHERE user_id = ? AND mention_type = 'role' AND guild_id = ?
                ORDER BY mention_count DESC LIMIT 1
            ''', (user_stats['user_id'], user_stats['guild_id']))
            top_role = cursor.fetchone()

            if top_role:
                try:
                    role_name = None
                    role_id = int(top_role[0])
                    for guild in self.bot.guilds:
                        role = guild.get_role(role_id)
                        if role:
                            role_name = role.name
                            break
                    role_text = f"{role_name} ({top_role[1]:,})" if role_name else f"Unknown Role ({top_role[1]:,})"
                    role_card = await create_metric_card(
                        "Most Mentioned Role",
                        role_text,
                        **get_card_settings('mentions')
                    )
                    await send_card(role_card, user)
                except Exception as e:
                    logging.error(f"Failed to create role card: {e}")

            try:
                stats_dict = {
                    "Messages Sent": user_stats['messages_sent'],
                    "Reactions Added": user_stats['reactions_added'],
                    "Voice Chat Hours": voice_hours,
                    "Stream Hours": stream_hours,
                    "Deafen Hours": deafen_hours,
                    "Personality Type": primary_trait
                }

                if secondary_traits_list:
                    stats_dict["Notable Traits"] = " • ".join(secondary_traits_list)

                if top_users:
                    try:
                        mentioned_user = await self.bot.fetch_user(top_users[0][0])
                        stats_dict["Most Mentioned User"] = f"{mentioned_user.name} ({top_users[0][1]})"
                    except Exception as e:
                        logging.error(f"Failed to fetch most mentioned user: {e}")

                if top_role and role_name:
                    stats_dict["Most Mentioned Role"] = role_text

                summary_card = await create_summary_card(stats_dict, **get_card_settings('messages', for_summary=True))  # Use messages style for summary
                if send_dm:
                    await send_card(summary_card, user, "And here's your year in summary! 🎉")
                else:
                    await send_card(summary_card, user)
            except Exception as e:
                logging.error(f"Failed to create summary card: {e}")

        except discord.Forbidden:
            logging.error(f"Cannot send DM to user {user_stats['user_id']}")
        except Exception as e:
            logging.error(f"Failed to process user {user_stats['user_id']}: {str(e)}")
            if interaction:
                await interaction.followup.send(f"Error processing user {user_stats['user_id']}: {str(e)}")

    async def wrap(self, interaction: discord.Interaction):
        if interaction.user.id not in self.config.ADMIN_IDS:
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return

        cursor = self.bot.db.cursor()
        cursor.execute('''
            SELECT user_id, guild_id, messages_sent, reactions_added, 
                   voice_time, stream_time, deafen_time, opt_in_date 
            FROM user_stats 
            WHERE opt_in_date IS NOT NULL AND guild_id = ?
        ''', (interaction.guild_id,))
        opted_in_users = cursor.fetchall()

        await interaction.response.send_message("Sending wraps to all opted-in users...", ephemeral=True)
        for user_stats in opted_in_users:
            await self.process_user_stats(dict(user_stats), send_dm=True)

    async def allwrap(self, interaction: discord.Interaction):
        if not self.config.DEBUG:
            return  

        if interaction.user.id not in self.config.ADMIN_IDS:
            await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        cursor = self.bot.db.cursor()
        cursor.execute('''
            SELECT user_id, guild_id, messages_sent, reactions_added, 
                   voice_time, stream_time, deafen_time, opt_in_date 
            FROM user_stats 
            WHERE opt_in_date IS NOT NULL AND guild_id = ?
        ''', (interaction.guild_id,))
        users_stats = cursor.fetchall()

        for user_stats in users_stats:
            await self.process_user_stats(dict(user_stats), interaction=interaction)

        await interaction.followup.send("All user stats have been processed.")

COLOR_PALETTES = {
    'default': {
        'colors': {
            'messages': '#5865F2',  # Discord Blurple
            'reactions': '#57F287', # Vibrant Green
            'voice': '#EB459E',     # Deep Pink
            'deafen': '#FFA500',    # Warm Orange
            'stream': '#3498db',    # Light Blue
            'mentions': '#FEE75C',  # Golden Yellow
            'replies': '#ED4245'    # Soft Red
        },
        'text_color': '#FFFFFF',    # White text
        'animation_speed': 1.0,
        'wave_intensity': 0.5,
        'card_style': 'classic',
        'font_size': 24
    },
    'spotify': {
        'colors': {
            'messages': '#1DB954',  # Spotify Green
            'reactions': '#1ED760', # Lighter Green
            'voice': '#2EBD59',     # Alt Green
            'deafen': '#1AA34A',    # Dark Green
            'stream': '#1DB954',    # Main Green
            'mentions': '#1ED760',  # Bright Green
            'replies': '#1AA34A'    # Deep Green
        },
        'text_color': '#FFFFFF',    # White text
        'animation_speed': 1.2,     # Slightly faster
        'wave_intensity': 0.6,      # More intense waves
        'card_style': 'modern',
        'font_size': 26
    },
    'pastel': {
        'colors': {
            'messages': '#FFB5E8',  # Pastel Pink
            'reactions': '#B5DEFF', # Pastel Blue
            'voice': '#E7FFAC',     # Pastel Green
            'deafen': '#FFC9DE',    # Light Pink
            'stream': '#A79AFF',    # Pastel Purple
            'mentions': '#FFABAB',  # Pastel Red
            'replies': '#85E3FF'    # Light Blue
        },
        'text_color': '#FFFFFF',    # White text
        'animation_speed': 0.8,     # Slower, gentler
        'wave_intensity': 0.4,      # Softer waves
        'card_style': 'classic',
        'font_size': 24
    },
    'neon': {
        'colors': {
            'messages': '#FF1B8D',  # Neon Pink
            'reactions': '#00FF9F', # Neon Green
            'voice': '#00F3FF',     # Neon Blue
            'deafen': '#FF8400',    # Neon Orange
            'stream': '#FF00FF',    # Neon Purple
            'mentions': '#FFFF00',  # Neon Yellow
            'replies': '#FF0000'    # Neon Red
        },
        'text_color': '#FFFFFF',    # White text
        'animation_speed': 1.5,     # Faster
        'wave_intensity': 0.8,      # Strong waves
        'card_style': 'modern',
        'font_size': 28
    },
    'monochrome': {
        'colors': {
            'messages': '#000000',  # Black
            'reactions': '#333333', # Dark Gray
            'voice': '#666666',     # Medium Gray
            'deafen': '#999999',    # Light Gray
            'stream': '#CCCCCC',    # Very Light Gray
            'mentions': '#444444',  # Alt Dark Gray
            'replies': '#888888'    # Alt Medium Gray
        },
        'text_color': '#FFFFFF',    # White text
        'animation_speed': 1.0,
        'wave_intensity': 0.3,      # Subtle waves
        'card_style': 'classic',
        'font_size': 24
    }
}
