import os
import uuid
import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from PIL import Image
from backend.config import settings
from backend.utils.response import api_response
from backend.routes.dependencies import get_current_admin

router = APIRouter(prefix="/upload", tags=["Upload"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

@router.post("", dependencies=[Depends(get_current_admin)])
async def upload_image(file: UploadFile = File(...)):
    # Validate file size
    # We can check size by seeking if needed, or by reading a chunk
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        return api_response(
            success=False,
            message="File size exceeds maximum allowed size (5MB)",
            status_code=400
        )
        
    # Get extension
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return api_response(
            success=False,
            message=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            status_code=400
        )
        
    # Ensure upload folder exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Generate unique filename
    unique_id = uuid.uuid4().hex
    filename = f"{unique_id}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)
    
    # Generate thumbnail name
    thumb_filename = f"{unique_id}_thumb{ext}"
    thumb_filepath = os.path.join(settings.UPLOAD_DIR, thumb_filename)
    
    # Save files
    try:
        # Write temporary file to open with Pillow
        with open(filepath, "wb") as f:
            f.write(content)
            
        # Process image with Pillow
        with Image.open(filepath) as img:
            # 1. Resize main image if it exceeds 1080px
            img.thumbnail((1080, 1080))
            img.save(filepath)
            
            # 2. Generate and save thumbnail
            img.thumbnail((300, 300))
            img.save(thumb_filepath)
            
        # Convert path to web format
        web_path = f"/static/uploads/{filename}"
        web_thumb_path = f"/static/uploads/{thumb_filename}"
        
        return api_response(
            success=True,
            message="Image uploaded successfully",
            data={
                "url": web_path,
                "thumbnail_url": web_thumb_path
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing image upload: {e}")
        # Clean up files if created
        if os.path.exists(filepath):
            os.remove(filepath)
        if os.path.exists(thumb_filepath):
            os.remove(thumb_filepath)
            
        return api_response(
            success=False,
            message="An error occurred while processing the image",
            errors=str(e),
            status_code=500
        )
