import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Dict
from app.schemas.common import ResponseModel
from app.core.dependencies import get_current_admin
from app.core.config import settings
import uuid

router = APIRouter(prefix="/upload", tags=["upload"], dependencies=[Depends(get_current_admin)])

@router.post("/image", response_model=ResponseModel[Dict[str, str]])
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    url = f"{settings.BASE_URL}/uploads/{filename}"
    return ResponseModel(data={"url": url}, message="Image uploaded successfully")
