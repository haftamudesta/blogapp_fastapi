import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status
from config import settings
import asyncio

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
    try:
        file_content = await file.read()
        
        # Upload to Cloudinary (run in thread pool since it's synchronous)
        upload_result = await asyncio.to_thread(
            cloudinary.uploader.upload,
            file_content,
            folder="blog_comments",  # Organize uploads in a folder
            allowed_formats=["jpg", "jpeg", "png", "gif", "webp"],
            transformation=[
                {"width": 500, "height": 500, "crop": "limit"},  # Resize if needed
                {"quality": "auto"}  
            ]
        )
        
        return upload_result['secure_url']
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading image: {str(e)}"
        )