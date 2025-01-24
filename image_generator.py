from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import io
import discord
import asyncio
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


STAT_COLORS = {

    'messages': (88, 101, 242),    # Discord Blurple
    'reactions': (87, 242, 135),   # Vibrant Green
    

    'voice': (235, 69, 158),       # Deep Pink
    'voice_time': (235, 69, 158),  # Deep Pink
    'deafen': (254, 128, 25),      # Warm Orange
    'stream': (88, 205, 242),      # Light Blue
    

    'mentions': (255, 172, 51),    # Golden Yellow
    'replies': (242, 87, 87),      # Soft Red
    

    'default': (29, 185, 84),      # Spotify Green
    'primary': (88, 101, 242),     # Discord Blurple
    'secondary': (153, 170, 181),  # Cool Gray
    'success': (87, 242, 135),     # Vibrant Green
    'warning': (255, 172, 51),     # Golden Yellow
    'error': (242, 87, 87),        # Soft Red
}

def get_stat_color(stat_type):
    """Get the color for a specific stat type."""
    return STAT_COLORS.get(stat_type.lower(), STAT_COLORS['default'])

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(SCRIPT_DIR, 'resources')

def get_resource_path(filename):
    """Get the absolute path to a resource file."""
    path = os.path.join(RESOURCES_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Resource not found: {filename} (looked in {path})")
    return path

def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_width = draw.textlength(" ".join(current_line), font=font)
        if line_width > max_width:
            if len(current_line) == 1:
                lines.append(current_line[0])
                current_line = []
            else:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
    
    if current_line:
        lines.append(" ".join(current_line))
    return lines

async def create_metric_card(
    title, 
    value, 
    stat_type='default',
    background_color=None,
    text_color=(255, 255, 255),
    animation_speed=1.0,
    wave_intensity=0.5,
    card_style='classic',
    font_size=24
):

    try:
        # Use stat-specific color if background_color is not provided
        if background_color is None:
            background_color = get_stat_color(stat_type)
            
        logger.debug(f"Starting card generation with params: title={title}, value={value}, style={card_style}, stat_type={stat_type}")
        
        # Load base template
        template_path = get_resource_path("basecard.png")
        logger.debug(f"Loading base template from {template_path}")
        base_template = Image.open(template_path).convert('RGBA')
        width, height = base_template.size
        
        # Load fonts
        try:
            title_font = ImageFont.truetype(get_resource_path("fonts/Inter_28pt-Regular.ttf"), font_size)
            value_font = ImageFont.truetype(get_resource_path("fonts/Inter_24pt-Bold.ttf"), int(font_size * 2.5))
        except Exception as e:
            logger.error(f"Error loading fonts: {e}")
            raise
        
        frames = []
        logger.debug("Generating wave patterns...")
        
        x = np.linspace(0, width, width)
        y = np.linspace(0, height, height)
        X, Y = np.meshgrid(x, y)
        flow_angle = np.random.uniform(0, 2 * np.pi)
        flow_x = np.cos(flow_angle)
        flow_y = np.sin(flow_angle)

        static_wave1 = np.sin((X*flow_x + Y*flow_y)/120) * 0.2
        static_wave2 = np.sin((X*flow_y - Y*flow_x)/150) * 0.15
        static_wave3 = np.sin(((X+Y)*flow_x)/180) * 0.25
        static_wave4 = np.cos((X*flow_x + Y*flow_y)/90) * 0.2
        
        static_combined = (static_wave1 + static_wave2 + static_wave3 + static_wave4)
        static_combined = np.tanh(static_combined) * 0.7 + 0.5
        
        static_r = (static_combined * background_color[0] * 0.8).astype(np.uint8)
        static_g = (static_combined * background_color[1] * 0.8).astype(np.uint8)
        static_b = (static_combined * background_color[2] * 0.8).astype(np.uint8)
        static_array = np.stack((static_r, static_g, static_b, np.full_like(static_r, 255)), axis=-1)
        static_blob = Image.fromarray(static_array)
        static_blob = static_blob.filter(ImageFilter.GaussianBlur(radius=2.5))
        
        content_mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(content_mask)
        mask_draw.rounded_rectangle([40, 192, width-40, height-125], radius=20, fill=255)

        wave_scale = wave_intensity * 0.5

        num_frames = int(30 / animation_speed)
        frame_duration = int(90 * animation_speed)
        
        logger.debug(f"Generating {num_frames} frames...")
        
        for i in range(num_frames):
            time = i * 0.1 * animation_speed
            wave1 = np.sin((X*flow_x + Y*flow_y)/120 + time) * 0.2 * wave_scale
            wave2 = np.sin((X*flow_y - Y*flow_x)/150 + time * 0.5) * 0.15 * wave_scale
            wave3 = np.sin(((X+Y)*flow_x)/180 + time * 0.8) * 0.25 * wave_scale
            wave4 = np.cos((X*flow_x + Y*flow_y)/90 + time * 0.6) * 0.2 * wave_scale
            combined_wave = (wave1 + wave2 + wave3 + wave4)
            combined_wave = np.tanh(combined_wave) * 0.7 + 0.5

            r = (combined_wave * background_color[0] * 0.8).astype(np.uint8)
            g = (combined_wave * background_color[1] * 0.8).astype(np.uint8)
            b = (combined_wave * background_color[2] * 0.8).astype(np.uint8)
            array = np.stack((r, g, b, np.full_like(r, 255)), axis=-1)
            background = Image.fromarray(array)
            background = background.filter(ImageFilter.GaussianBlur(radius=2.5))

            img = background.copy()
            img = Image.alpha_composite(img, base_template)

            content = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            content.paste(static_blob, (0, 0), content_mask)

            rings_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            rings_draw = ImageDraw.Draw(rings_overlay)

            center_x = width // 2
            center_y = height // 2

            if card_style != 'minimal':  # No rings in minimal style
                # Draw multiple expanding rings
                num_rings = 8 if card_style == 'modern' else 6
                max_radius = 300 if card_style == 'modern' else 250
                for ring in range(num_rings):
                    ring_progress = (time * 0.3 + (ring * 1.0 / num_rings)) % 2.0
                    radius = ring_progress * max_radius
                    if ring_progress < 1.0:
                        ring_opacity = int(255 * ring_progress)
                    else:
                        ring_opacity = int(255 * (2.0 - ring_progress))
                    distance_fade = 1.0 - (radius / max_radius)
                    ring_opacity = int(ring_opacity * distance_fade)
                    if ring_opacity > 0:
                        bbox = [
                            center_x - radius,
                            center_y - radius,
                            center_x + radius,
                            center_y + radius
                        ]
                        ring_width = 3 if card_style == 'modern' else 2
                        rings_draw.ellipse(bbox, outline=text_color + (ring_opacity,), width=ring_width)

            # Composite content area with rings
            content = Image.alpha_composite(content, rings_overlay)
            img.paste(content, (0, 0), content_mask)

            # Add text overlay
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            safe_width = width - 120

            wrapped_title = wrap_text(title, title_font, draw, safe_width)
            wrapped_value = wrap_text(str(value), value_font, draw, safe_width)

            # Calculate total heights needed
            value_total_height = len(wrapped_value) * (value_font.size + 10) - 10
            title_total_height = len(wrapped_title) * (title_font.size + 10) - 10

            # Adjust text positions based on style
            if card_style == 'modern':
                value_y = height - 340
                title_y = height - 200
            elif card_style == 'minimal':
                value_y = height - 300
                title_y = height - 160
            else:  # classic
                value_y = height - 320
                title_y = height - 180

            # Apply text animations based on style
            if card_style == 'minimal':
                title_opacity = 255
                value_opacity = 255
            else:
                title_opacity = min(255, int((i / 10) * 255))
                value_opacity = 0 if i < 15 else min(255, int(((i - 15) / 15) * 255))

            for line in wrapped_title:
                line_bbox = draw.textbbox((0, 0), line, font=title_font)
                line_x = (width - (line_bbox[2] - line_bbox[0])) // 2
                draw.text((line_x, title_y), line, font=title_font, fill=text_color + (title_opacity,))
                title_y += title_font.size + 10

            for line in wrapped_value:
                line_bbox = draw.textbbox((0, 0), line, font=value_font)
                line_x = (width - (line_bbox[2] - line_bbox[0])) // 2
                draw.text((line_x, value_y), line, font=value_font, fill=text_color + (value_opacity,))
                value_y += value_font.size + 10

            img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
            frames.append(img)

            if i % 10 == 0:
                logger.debug(f"Generated frame {i}/{num_frames}")
        
        logger.debug("Creating final GIF...")
        # Create buffer for the final GIF
        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration,
            loop=0,
            quality=100,
            optimize=False
        )
        buffer.seek(0)
        
        logger.debug("Card generation complete")
        return discord.File(buffer, filename='stat_card.gif')
        
    except Exception as e:
        logger.error(f"Error in create_metric_card: {str(e)}", exc_info=True)
        raise

async def create_mentions_card(title, mentions, fetch_avatar, resolve_name=None, background_color=(54, 57, 63)):
    """Create an animated card showing user mentions statistics.
    
    Args:
        title (str): The title to display on the card
        mentions (list): List of tuples containing (user_id, mention_count)
        fetch_avatar (callable): Async function to fetch user avatars
        resolve_name (callable, optional): Async function to resolve user names. Defaults to None.
        background_color (tuple, optional): RGB color tuple for background. Defaults to Discord dark theme color.
    
    Returns:
        discord.File: The generated animated GIF as a Discord file attachment.
    """
    base_template = Image.open(get_resource_path("basecard.png")).convert('RGBA')
    width, height = base_template.size
    frames = []
    
    # Create static blob for content area
    x = np.linspace(0, width, width)
    y = np.linspace(0, height, height)
    X, Y = np.meshgrid(x, y)
    
    flow_angle = np.random.uniform(0, 2 * np.pi)
    flow_x = np.cos(flow_angle)
    flow_y = np.sin(flow_angle)
    
    # Generate static wave pattern for content area
    static_wave1 = np.sin((X*flow_x + Y*flow_y)/120) * 0.2
    static_wave2 = np.sin((X*flow_y - Y*flow_x)/150) * 0.15
    static_wave3 = np.sin(((X+Y)*flow_x)/180) * 0.25
    static_wave4 = np.cos((X*flow_x + Y*flow_y)/90) * 0.2
    
    static_combined = (static_wave1 + static_wave2 + static_wave3 + static_wave4)
    static_combined = np.tanh(static_combined) * 0.7 + 0.5
    
    # Create static content blob
    static_r = (static_combined * background_color[0] * 0.8).astype(np.uint8)
    static_g = (static_combined * background_color[1] * 0.8).astype(np.uint8)
    static_b = (static_combined * background_color[2] * 0.8).astype(np.uint8)
    static_array = np.stack((static_r, static_g, static_b, np.full_like(static_r, 255)), axis=-1)
    static_blob = Image.fromarray(static_array)
    static_blob = static_blob.filter(ImageFilter.GaussianBlur(radius=2.5))
    
    # Create content mask
    content_mask = Image.new('L', (width, height), 0)
    mask_draw = ImageDraw.Draw(content_mask)
    mask_draw.rounded_rectangle([40, 192, width-40, height-125], radius=20, fill=255)
    
    title_font = ImageFont.truetype(get_resource_path("fonts/Inter_28pt-Regular.ttf"), 24)
    mention_font = ImageFont.truetype(get_resource_path("fonts/Inter_24pt-Bold.ttf"), 16)
    
    # Fetch all user data once at the start
    user_data = []
    for mention_id, mention_count in mentions[:5]:
        await asyncio.sleep(1)
        avatar_bytes = None
        user_name = str(mention_id)
        
        if fetch_avatar:
            avatar_bytes = await fetch_avatar(mention_id)
            if resolve_name:
                user = await resolve_name(mention_id)
                user_name = user.name if user else str(mention_id)
        
        avatar_img = None
        if avatar_bytes:
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).resize((48, 48))
            
        user_data.append({
            'name': user_name,
            'count': mention_count,
            'avatar': avatar_img
        })
    
    # Grid parameters
    grid_size = 40
    grid_spacing = 60
    
    for i in range(45):
        # Create animated background first
        time = i * 0.1
        wave1 = np.sin((X*flow_x + Y*flow_y)/120 + time) * 0.2
        wave2 = np.sin((X*flow_y - Y*flow_x)/150 + time * 0.5) * 0.15
        wave3 = np.sin(((X+Y)*flow_x)/180 + time * 0.8) * 0.25
        wave4 = np.cos((X*flow_x + Y*flow_y)/90 + time * 0.6) * 0.2
        
        combined_wave = (wave1 + wave2 + wave3 + wave4)
        combined_wave = np.tanh(combined_wave) * 0.7 + 0.5
        
        r = (combined_wave * background_color[0] * 0.8).astype(np.uint8)
        g = (combined_wave * background_color[1] * 0.8).astype(np.uint8)
        b = (combined_wave * background_color[2] * 0.8).astype(np.uint8)
        array = np.stack((r, g, b, np.full_like(r, 255)), axis=-1)
        background = Image.fromarray(array)
        background = background.filter(ImageFilter.GaussianBlur(radius=2.5))
        
        # Start with animated background
        img = background.copy()
        
        # Paste template over background
        img = Image.alpha_composite(img, base_template)
        
        # Create content area with static blob
        content = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        content.paste(static_blob, (0, 0), content_mask)
        
        # Create grid overlay
        grid_overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        grid_draw = ImageDraw.Draw(grid_overlay)
        
        # Draw animated grid
        offset_x = (time * 20) % grid_spacing
        offset_y = (time * 20) % grid_spacing
        
        for x in range(int(-grid_spacing + offset_x), width + grid_spacing, grid_spacing):
            opacity = int(255 * (0.5 + 0.5 * np.cos(x / 100 + time)))
            grid_draw.line([(x, 192), (x, height-125)], fill=(255, 255, 255, opacity), width=1)
            
        for y in range(int(-grid_spacing + offset_y), height, grid_spacing):
            opacity = int(255 * (0.5 + 0.5 * np.cos(y / 100 + time)))
            grid_draw.line([(40, y), (width-40, y)], fill=(255, 255, 255, opacity), width=1)
        
        # Composite content area with grid
        content = Image.alpha_composite(content, grid_overlay)
        img.paste(content, (0, 0), content_mask)
        
        # Add mentions with bounce animation
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        mention_opacity = min(255, int((i / 10) * 255))
        
        # Calculate bounce effect
        bounce_progress = i / 30
        bounce_offset = int(20 * np.sin(bounce_progress * np.pi) * (1 - bounce_progress))
        
        # Draw title with bounce
        title_y = height - 210 + bounce_offset
        wrapped_title = wrap_text(title, title_font, draw, width - 120)
        for line in wrapped_title:
            line_bbox = draw.textbbox((0, 0), line, font=title_font)
            line_x = (width - (line_bbox[2] - line_bbox[0])) // 2
            draw.text((line_x, title_y), line, font=title_font, fill=(255, 255, 255, mention_opacity))
            title_y += title_font.size + 5
        
        # Start mentions list with staggered bounce
        base_y_offset = height - 510
        avatar_size = 48
        padding = 12
        
        for idx, user in enumerate(user_data):
            item_bounce = int(20 * np.sin((bounce_progress - idx * 0.1) * np.pi) * 
                            max(0, 1 - (bounce_progress - idx * 0.1)))
            y_offset = base_y_offset + (idx * (avatar_size + padding)) + item_bounce
            
            if y_offset + avatar_size + padding > height - 180:
                break
                
            x_offset = 80
            
            if user['avatar']:
                mask = Image.new('L', (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=mention_opacity)
                
                output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
                output.paste(user['avatar'], (0, 0))
                output.putalpha(mask)
                
                img.paste(output, (x_offset, y_offset), output)
            
            mention_text = f"{user['name']} - {user['count']:,} mentions"
            draw.text((x_offset + avatar_size + padding, y_offset + 12), 
                     mention_text, font=mention_font, fill=(255, 255, 255, mention_opacity))
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        frames.append(img)
    
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=90,
        loop=1,
        quality=100,
        optimize=False
    )
    buffer.seek(0)
    return discord.File(buffer, filename='mentions_card.gif')

async def create_summary_card(stats_dict, background_color=(29, 185, 84)):
    width = 1920
    height = 1080
    
    x = np.linspace(0, width, width)
    y = np.linspace(0, height, height)
    X, Y = np.meshgrid(x, y)
    
    flow_angle = np.random.uniform(0, 2 * np.pi)
    flow_x = np.cos(flow_angle)
    flow_y = np.sin(flow_angle)
    
    wave1 = np.sin((X*flow_x + Y*flow_y)/120) * 0.2
    wave2 = np.sin((X*flow_y - Y*flow_x)/150) * 0.15
    wave3 = np.sin(((X+Y)*flow_x)/180) * 0.25
    wave4 = np.cos((X*flow_x + Y*flow_y)/90) * 0.2
    
    combined_wave = (wave1 + wave2 + wave3 + wave4)
    combined_wave = np.tanh(combined_wave) * 0.7 + 0.5
    
    r = (combined_wave * background_color[0] * 0.8).astype(np.uint8)
    g = (combined_wave * background_color[1] * 0.8).astype(np.uint8)
    b = (combined_wave * background_color[2] * 0.8).astype(np.uint8)
    array = np.stack((r, g, b), axis=-1)
    img = Image.fromarray(array)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.5))
    
    draw = ImageDraw.Draw(img)
    
    try:
        title_font = ImageFont.truetype(get_resource_path("fonts/Inter_28pt-Regular.ttf"), 72)
        label_font = ImageFont.truetype(get_resource_path("fonts/Inter_28pt-Regular.ttf"), 48)
        value_font = ImageFont.truetype(get_resource_path("fonts/Inter_24pt-Bold.ttf"), 64)
        personality_font = ImageFont.truetype(get_resource_path("fonts/Inter_24pt-Bold.ttf"), 86)
    except Exception as e:
        logger.error(f"Error loading fonts: {e}")
        raise
    
    title = "Your Year in Review"
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 40), title, font=title_font, fill=(255, 255, 255))
    
    current_y = 180

    if "Personality Type" in stats_dict:
        personality = stats_dict.pop("Personality Type")
        personality_bbox = draw.textbbox((0, 0), personality, font=personality_font)
        personality_x = (width - personality_bbox[2] + personality_bbox[0]) // 2
        draw.text((personality_x, current_y), personality, font=personality_font, fill=(255, 255, 255))
        current_y += 100
        
        if "Notable Traits" in stats_dict:
            traits = stats_dict.pop("Notable Traits")
            traits_bbox = draw.textbbox((0, 0), traits, font=label_font)
            traits_x = (width - traits_bbox[2] + traits_bbox[0]) // 2
            draw.text((traits_x, current_y), traits, font=label_font, fill=(255, 255, 255))
            current_y += 80
    
    margin = 60
    grid_width = width - (2 * margin)
    column_width = (grid_width - margin) // 2
    row_height = 120
    
    current_x = margin
    for label, value in stats_dict.items():
        draw.text((current_x, current_y), label, font=label_font, fill=(255, 255, 255, 200))
        
        value_str = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        draw.text((current_x, current_y + 50), value_str, font=value_font, fill=(255, 255, 255))
        
        if current_x + column_width + margin >= width - margin:
            current_x = margin
            current_y += row_height + 20
        else:
            current_x += column_width + margin
    
    try:
        logo_path = get_resource_path("wrappedlogowhite.png")
        logo = Image.open(logo_path).convert('RGBA')
        logo_width = 200
        logo_height = int(logo.height * (logo_width / logo.width))
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        logo_x = width - logo_width - 40
        logo_y = height - logo_height - 40
        img.paste(logo, (logo_x, logo_y), logo)
    except Exception as e:
        logger.error(f"Error loading or pasting logo: {e}")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return discord.File(buffer, filename='summary_card.png')