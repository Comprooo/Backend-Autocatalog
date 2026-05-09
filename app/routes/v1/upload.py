import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Dict, List
from app.schemas.common import ResponseModel
from app.core.dependencies import get_current_admin
from app.core.config import settings
import cloudinary
import cloudinary.uploader
import uuid

router = APIRouter(prefix="/upload", tags=["upload"], dependencies=[Depends(get_current_admin)])

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

@router.post("/image", response_model=ResponseModel[Dict[str, str]])
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Upload directly to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file.file,
            folder="autocatalog",
            public_id=f"{uuid.uuid4()}"
        )
        url = upload_result.get("secure_url")
        return ResponseModel(data={"url": url}, message="Image uploaded to Cloudinary successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

@router.post("/images", response_model=ResponseModel[List[Dict[str, str]]])
async def upload_images(files: List[UploadFile] = File(...)):
    results = []
    
    for file in files:
        if not file.content_type.startswith("image/"):
            continue
            
        try:
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder="autocatalog",
                public_id=f"{uuid.uuid4()}"
            )
            url = upload_result.get("secure_url")
            results.append({"url": url, "filename": file.filename})
        except Exception:
            # Skip failed uploads in bulk
            continue
        
    return ResponseModel(data=results, message=f"{len(results)} images uploaded to Cloudinary successfully")
