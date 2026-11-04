import os
ALLOWED = {"image/jpeg", "image/png", "image/webp"}

def configured():
    return bool(os.environ.get("CLOUDINARY_URL"))

def upload(f, folder):
    """Upload an image file to Cloudinary; returns its https URL. Reads CLOUDINARY_URL from env."""
    import cloudinary.uploader
    if f.mimetype not in ALLOWED:
        raise ValueError("type")
    return cloudinary.uploader.upload(f.stream, folder=folder, resource_type="image")["secure_url"]
