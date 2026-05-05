# generate_icons.py - Run once to create placeholder icons
from PIL import Image, ImageDraw, ImageFont
import os


def create_icon(size, filename):
    img = Image.new('RGB', (size, size), color='#0D1B2A')
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for i in range(size):
        color = (13 + i * 50 // size, 27 + i * 50 // size, 42 + i * 50 // size)
        draw.rectangle([(0, i), (size, i)], fill=color)

    # Draw snowflake symbol
    draw.ellipse([(size // 4, size // 4), (size * 3 // 4, size * 3 // 4)], outline='#00B4D8', width=max(1, size // 20))
    draw.line([(size // 2, size // 6), (size // 2, size * 5 // 6)], fill='#00B4D8', width=max(1, size // 20))
    draw.line([(size // 6, size // 2), (size * 5 // 6, size // 2)], fill='#00B4D8', width=max(1, size // 20))

    # Draw text
    try:
        font = ImageFont.truetype("arial.ttf", size // 4)
        draw.text((size // 2.5, size // 2.5), "❄️", fill='white', font=font)
    except:
        draw.text((size // 3, size // 3), "LT", fill='white')

    img.save(f'static/{filename}')
    print(f"Created {filename}")


os.makedirs('static', exist_ok=True)
sizes = [72, 96, 128, 144, 152, 192, 384, 512]
for size in sizes:
    create_icon(size, f'icon-{size}.png')
print("All icons created!")

