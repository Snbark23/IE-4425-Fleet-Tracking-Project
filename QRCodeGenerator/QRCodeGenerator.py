import qrcode
from PIL import Image, ImageDraw, ImageSequence
import random
import os

def generate_confetti_frame(size=(600, 600), dot_count=200):
    frame = Image.new('RGB', size, 'white')
    draw = ImageDraw.Draw(frame)
    for _ in range(dot_count):
        x = random.randint(0, size[0])
        y = random.randint(0, size[1])
        radius = random.randint(2, 6)
        color = random.choice(['blue', 'white'])
        draw.ellipse((x, y, x + radius, y + radius), fill=color)
    return frame

def create_qr_with_logo(data, logo_path, size=(300, 300)):
    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    qr_img = qr_img.resize(size, Image.LANCZOS)

    logo = Image.open(logo_path)
    logo_size = size[0] // 4
    logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
    pos = ((qr_img.size[0] - logo_size) // 2, (qr_img.size[1] - logo_size) // 2)
    qr_img.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)
    
    return qr_img

def create_qr_gif(data, logo_path, output_path='QRCodeGenerator/animated_qr.gif', frame_count=12):
    # Create directory
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Create QR code with logo
    qr_img = create_qr_with_logo(data, logo_path)

    # Generate frames with QR over confetti
    frames = []
    for _ in range(frame_count):
        bg = generate_confetti_frame()
        bg = bg.convert('RGBA')
        pos = ((bg.width - qr_img.width) // 2, (bg.height - qr_img.height) // 2)
        bg.paste(qr_img, pos, qr_img)
        frames.append(bg)

    # Save animated GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=150,
        loop=0,
        disposal=2
    )
    print(f"Animated QR Code GIF saved to: {output_path}")

# Run it
create_qr_gif(
    data="https://ie4425termproject.onrender.com/sign-up",
    logo_path="website/static/logo.png",
    output_path="QRCodeGenerator/animated_qr.gif"
)
