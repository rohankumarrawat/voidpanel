import os
from PIL import Image

src_icon = '/Users/rohan/Desktop/voidpanel/voidmail_app/assets/google_console_icon.png'
if not os.path.exists(src_icon):
    src_icon = '/Users/rohan/Desktop/voidpanel/voidmail_app/assets/icon/google_console_icon.png'

print(f"Source icon: {src_icon}")
img = Image.open(src_icon)

res_dir = '/Users/rohan/Desktop/voidpanel/voidmail_app/android/app/src/main/res'

sizes = {
    'mipmap-mdpi': (48, 48),
    'mipmap-hdpi': (72, 72),
    'mipmap-xhdpi': (96, 96),
    'mipmap-xxhdpi': (144, 144),
    'mipmap-xxxhdpi': (192, 192)
}

for folder, size in sizes.items():
    target_dir = os.path.join(res_dir, folder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, 'ic_launcher.png')
    resized = img.resize(size, Image.Resampling.LANCZOS)
    resized.save(target_path, 'PNG')
    print(f"Generated {target_path} ({size[0]}x{size[1]})")

# iOS AppIcon assets
ios_dir = '/Users/rohan/Desktop/voidpanel/voidmail_app/ios/Runner/Assets.xcassets/AppIcon.appiconset'
if os.path.exists(ios_dir):
    ios_sizes = [
        ('Icon-App-20x20@1x.png', 20),
        ('Icon-App-20x20@2x.png', 40),
        ('Icon-App-20x20@3x.png', 60),
        ('Icon-App-29x29@1x.png', 29),
        ('Icon-App-29x29@2x.png', 58),
        ('Icon-App-29x29@3x.png', 87),
        ('Icon-App-40x40@1x.png', 40),
        ('Icon-App-40x40@2x.png', 80),
        ('Icon-App-40x40@3x.png', 120),
        ('Icon-App-60x60@2x.png', 120),
        ('Icon-App-60x60@3x.png', 180),
        ('Icon-App-1024x1024@1x.png', 1024),
    ]
    for filename, sz in ios_sizes:
        t_path = os.path.join(ios_dir, filename)
        r_img = img.resize((sz, sz), Image.Resampling.LANCZOS)
        r_img.save(t_path, 'PNG')
        print(f"Generated iOS icon: {t_path}")

print("App Icon Generation Complete!")
