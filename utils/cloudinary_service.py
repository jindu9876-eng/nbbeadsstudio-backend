import os
import uuid
import logging
import httpx
from typing import Optional, Dict, Any
from io import BytesIO
from PIL import Image

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.api
    _HAS_CLOUDINARY = True
except ImportError:
    cloudinary = None
    _HAS_CLOUDINARY = False

from backend.config import settings

logger = logging.getLogger(__name__)

# Configure Cloudinary if credentials are present
def is_cloudinary_configured() -> bool:
    return bool(
        _HAS_CLOUDINARY
        and settings.CLOUDINARY_CLOUD_NAME 
        and settings.CLOUDINARY_API_KEY 
        and settings.CLOUDINARY_API_SECRET
        and settings.CLOUDINARY_CLOUD_NAME.strip()
    )

if is_cloudinary_configured():
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True
    )
    logger.info("Cloudinary configured successfully.")
else:
    logger.info("Cloudinary not configured or not installed. Using local storage fallback for images.")


def _save_local_file(content: bytes, filename: str) -> Dict[str, Any]:
    """Fallback local file storage when Cloudinary credentials are not set."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    _, ext = os.path.splitext(filename.lower())
    if not ext:
        ext = ".jpg"
        
    unique_id = uuid.uuid4().hex
    saved_name = f"{unique_id}{ext}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_name)
    
    thumb_name = f"{unique_id}_thumb{ext}"
    thumb_path = os.path.join(settings.UPLOAD_DIR, thumb_name)
    
    with open(saved_path, "wb") as f:
        f.write(content)
        
    try:
        with Image.open(saved_path) as img:
            img.thumbnail((1200, 1200))
            img.save(saved_path)
            
            img.thumbnail((300, 300))
            img.save(thumb_path)
    except Exception as e:
        logger.warning(f"Could not generate thumbnail with Pillow: {e}")
        
    return {
        "url": f"/static/uploads/{saved_name}",
        "thumbnail_url": f"/static/uploads/{thumb_name}",
        "public_id": unique_id,
        "provider": "local",
        "format": ext.replace(".", "")
    }


async def upload_image_file(
    content: bytes, 
    filename: str, 
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """Uploads an image file either to Cloudinary or to local storage fallback."""
    folder_name = folder or settings.CLOUDINARY_FOLDER
    
    if is_cloudinary_configured():
        try:
            # Reconfigure on each call in case env vars were updated at runtime
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            result = cloudinary.uploader.upload(
                content,
                folder=folder_name,
                resource_type="image",
                transformation=[
                    {"quality": "auto:good"},
                    {"fetch_format": "auto"}
                ]
            )
            return {
                "url": result.get("secure_url"),
                "thumbnail_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "provider": "cloudinary"
            }
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}. Falling back to local storage.")
            
    return _save_local_file(content, filename)


async def upload_image_from_url(
    image_url: str, 
    folder: Optional[str] = None
) -> Dict[str, Any]:
    """
    Downloads an image from a remote URL and uploads it to Cloudinary,
    or caches it in local storage fallback.
    """
    folder_name = folder or settings.CLOUDINARY_FOLDER
    
    if is_cloudinary_configured():
        try:
            cloudinary.config(
                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                api_key=settings.CLOUDINARY_API_KEY,
                api_secret=settings.CLOUDINARY_API_SECRET,
                secure=True
            )
            result = cloudinary.uploader.upload(
                image_url,
                folder=folder_name,
                resource_type="image",
                transformation=[
                    {"quality": "auto:good"},
                    {"fetch_format": "auto"}
                ]
            )
            return {
                "url": result.get("secure_url"),
                "thumbnail_url": result.get("secure_url"),
                "public_id": result.get("public_id"),
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "provider": "cloudinary"
            }
        except Exception as e:
            logger.error(f"Cloudinary URL upload failed ({e}). Attempting manual download.")

    # Download remote image content
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(image_url)
            if resp.status_code == 200:
                content = resp.content
                filename = image_url.split("?")[0].split("/")[-1] or "remote_image.jpg"
                if not any(filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    filename += ".jpg"
                return _save_local_file(content, filename)
    except Exception as e:
        logger.error(f"Failed to fetch image URL {image_url}: {e}")
        
    # Return original URL as fallback if download failed
    return {
        "url": image_url,
        "thumbnail_url": image_url,
        "public_id": "",
        "provider": "external"
    }
