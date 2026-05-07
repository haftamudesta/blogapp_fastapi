import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from config import settings
import asyncio
import tempfile
import os

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret
)

async def upload_comment_image(file: UploadFile) -> str:
    """
    Upload an image to Cloudinary and return the secure URL.
    """
    temp_file = None
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Validate file size (max 5MB)
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 5MB."
            )
        
        # Create temporary file
        file_extension = file.filename.split('.')[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp:
            tmp.write(file_content)
            temp_file = tmp.name
        
        # Upload to Cloudinary
        upload_result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            temp_file,
            folder="blog_comments",
            allowed_formats=["jpg", "jpeg", "png", "gif", "webp"],
            transformation=[
                {"width": 800, "height": 800, "crop": "limit"},
                {"quality": "auto"}
            ]
        )
        
        return upload_result['secure_url']
        
    except Exception as e:
        print(f"Cloudinary upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)