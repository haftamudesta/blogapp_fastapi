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
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Upload to Cloudinary
        image_url = await upload_comment_image(file)
        
        return {"url": image_url, "success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )