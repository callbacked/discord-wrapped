import discord
from discord import app_commands
from datetime import datetime
import logging
from config import Config
from database import Database
from commands import WrapCommands

class ActivityBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.config = Config()
        self.tree = app_commands.CommandTree(self)
        self.db = Database().db
        self.voice_states = {}
        self.stream_states = {}
        self.deafen_states = {}
        self.wrap_commands = WrapCommands(self, self.config)
        logging.info(f'Bot initialized in {self.config.ENV.upper()} mode')

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        commands = self.wrap_commands.get_commands()
        for command in commands:
            self.tree.add_command(command)
        await self.tree.sync()
        logging.info('Commands synced with Discord')

    async def on_ready(self):
        logging.info(f'Bot is ready! Logged in as {self.user.name}#{self.user.discriminator}')
        print(f'{self.user} is ready!')
        
        
        for guild in self.guilds:
            await self.sync_roles(guild)

    async def sync_roles(self, guild):
        """Sync roles from a guild to the database."""
        cursor = self.db.cursor()
        
    
        for role in guild.roles:
            cursor.execute('''
                INSERT INTO roles (id, guild_id, name)
                VALUES (?, ?, ?)
                ON CONFLICT(id, guild_id) 
                DO UPDATE SET name = ?, updated_at = CURRENT_TIMESTAMP
            ''', (role.id, guild.id, role.name, role.name))
        
        self.db.commit()
        logging.info(f'Synced {len(guild.roles)} roles for guild {guild.name}')

    async def on_guild_role_create(self, role):
        """Handle role creation."""
        cursor = self.db.cursor()
        cursor.execute('''
            INSERT INTO roles (id, guild_id, name)
            VALUES (?, ?, ?)
        ''', (role.id, role.guild.id, role.name))
        self.db.commit()
        logging.info(f'Added new role {role.name} to database')

    async def on_guild_role_update(self, before, after):
        """Handle role updates."""
        if before.name != after.name:  
            cursor = self.db.cursor()
            cursor.execute('''
                UPDATE roles 
                SET name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND guild_id = ?
            ''', (after.name, after.id, after.guild.id))
            self.db.commit()
            logging.info(f'Updated role name from {before.name} to {after.name}')

    async def on_guild_role_delete(self, role):
        """Handle role deletion."""
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM roles WHERE id = ? AND guild_id = ?', 
                      (role.id, role.guild.id))
        self.db.commit()
        logging.info(f'Deleted role {role.name} from database')

    async def on_message(self, message):
        if message.author.bot:
            return
            
        
        if not message.guild:
            return
            
        cursor = self.db.cursor()
        cursor.execute('SELECT opt_in_date FROM user_stats WHERE user_id = ? AND guild_id = ?', 
                      (message.author.id, message.guild.id))
        user_status = cursor.fetchone()
        
        if not user_status or not user_status[0]:
            return
            
        cursor.execute('UPDATE user_stats SET messages_sent = messages_sent + 1 WHERE user_id = ? AND guild_id = ?', 
                      (message.author.id, message.guild.id))
        
        for mentioned_user in message.mentions:
            cursor.execute('SELECT opt_in_date FROM user_stats WHERE user_id = ? AND guild_id = ?', 
                         (mentioned_user.id, message.guild.id))
            mentioned_status = cursor.fetchone()
            if mentioned_status and mentioned_status[0]:
                cursor.execute('''
                    INSERT INTO mention_stats (user_id, guild_id, mentioned_id, mention_type, mention_count)
                    VALUES (?, ?, ?, 'user', 1)
                    ON CONFLICT(user_id, guild_id, mentioned_id, mention_type)
                    DO UPDATE SET mention_count = mention_count + 1
                ''', (message.author.id, message.guild.id, mentioned_user.id))
        
        for mentioned_role in message.role_mentions:
            cursor.execute('''
                INSERT INTO mention_stats (user_id, guild_id, mentioned_id, mention_type, mention_count)
                VALUES (?, ?, ?, 'role', 1)
                ON CONFLICT(user_id, guild_id, mentioned_id, mention_type)
                DO UPDATE SET mention_count = mention_count + 1
            ''', (message.author.id, message.guild.id, mentioned_role.id))
        
        self.db.commit()
        logging.debug(f'Message count updated for opted-in user {message.author.display_name}({message.author.id})')

    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
            
        cursor = self.db.cursor()
        cursor.execute('SELECT opt_in_date FROM user_stats WHERE user_id = ? AND guild_id = ?', 
                      (user.id, reaction.message.guild.id))
        user_status = cursor.fetchone()
        
        if not user_status or not user_status[0]:
            return
            
        cursor.execute('UPDATE user_stats SET reactions_added = reactions_added + 1 WHERE user_id = ? AND guild_id = ?', 
                      (user.id, reaction.message.guild.id))
        self.db.commit()
        logging.info(f'Reaction count updated for opted-in user {user.display_name}({user.id})')

    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
            
        cursor = self.db.cursor()
        cursor.execute('SELECT opt_in_date FROM user_stats WHERE user_id = ? AND guild_id = ?', 
                      (member.id, member.guild.id))
        user_status = cursor.fetchone()
        
        if not user_status or not user_status[0]:
            return
            
        if before.channel is None and after.channel is not None:
            self.voice_states[member.id] = datetime.now()
            logging.info(f'Opted-in user {member.display_name}({member.id}) joined voice channel {after.channel.name}')
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_states:
                join_time = self.voice_states[member.id]
                duration = int((datetime.now() - join_time).total_seconds())
                cursor.execute('UPDATE user_stats SET voice_time = voice_time + ? WHERE user_id = ? AND guild_id = ?', 
                             (duration, member.id, member.guild.id))
                self.db.commit()
                del self.voice_states[member.id]
                logging.info(f'Opted-in user {member.display_name}({member.id}) left voice channel. Duration: {duration} seconds')

        if before.self_stream != after.self_stream:
            if after.self_stream:
                self.stream_states[member.id] = datetime.now()
                logging.info(f'Opted-in user {member.display_name}({member.id}) started streaming')
            else:
                if member.id in self.stream_states:
                    stream_start_time = self.stream_states[member.id]
                    stream_duration = int((datetime.now() - stream_start_time).total_seconds())
                    cursor.execute('UPDATE user_stats SET stream_time = stream_time + ? WHERE user_id = ? AND guild_id = ?', 
                                 (stream_duration, member.id, member.guild.id))
                    self.db.commit()
                    del self.stream_states[member.id]
                    logging.info(f'Opted-in user {member.display_name}({member.id}) stopped streaming. Duration: {stream_duration} seconds')

        if before.self_deaf != after.self_deaf:
            if after.self_deaf:
                self.deafen_states[member.id] = datetime.now()
                logging.info(f'Opted-in user {member.display_name}({member.id}) deafened themselves')
            else:
                if member.id in self.deafen_states:
                    deafen_start_time = self.deafen_states[member.id]
                    deafen_duration = int((datetime.now() - deafen_start_time).total_seconds())
                    cursor.execute('UPDATE user_stats SET deafen_time = deafen_time + ? WHERE user_id = ? AND guild_id = ?', 
                                 (deafen_duration, member.id, member.guild.id))
                    self.db.commit()
                    del self.deafen_states[member.id]
                    logging.info(f'Opted-in user {member.display_name}({member.id}) undeafened. Duration: {deafen_duration} seconds')

    async def on_command_error(self, interaction: discord.Interaction, error):
        logging.error(f'Command error for user {interaction.user.display_name}({interaction.user.id}): {str(error)}')
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)
