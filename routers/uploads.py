from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from services.cloudinary_service import upload_comment_image
from auth import get_current_user
import models

router = APIRouter()

@router.post("/comment-image")
async def upload_comment_image_endpoint(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    """
    Upload an image for a comment. Returns the image URL.
    """
    allowed_types = ["image/jpeg","image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        #content_type is built into HTTP and web standards
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPG, JPEG, PNG, GIF, and WebP are allowed."
        )
    
    file_content = await file.read()
    if len(file_content) > 5 * 1024 * 1024:  
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB."
        )
    
    # Reset file position after reading
    await file.seek(0)
    
    # Upload to Cloudinary
    image_url = await upload_comment_image(file)
    
    return {"url": image_url}