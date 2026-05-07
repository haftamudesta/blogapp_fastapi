import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from config import settings
import asyncio

# Configure Cloudinary
def configure_cloudinary():
    cloud_name = settings.cloudinary_cloud_name
    api_key = settings.cloudinary_api_key
    api_secret = settings.cloudinary_api_secret.get_secret_value() if settings.cloudinary_api_secret else ""
    
    if not cloud_name or not api_key or not api_secret:
        raise Exception("Cloudinary credentials not configured")
    
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )

async def upload_comment_image(file: UploadFile) -> str:
    """
    Upload an image to Cloudinary and return the secure URL.
    """
    try:
        # Configure Cloudinary
        configure_cloudinary()
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size (max 5MB)
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large. Maximum size is 5MB."
            )
        
        # Upload to Cloudinary
        upload_result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_content,
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