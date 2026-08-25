from fastapi import APIRouter, Depends, HTTPException, status, Request


router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(request: Request):
    """
    Health check endpoint to verify if the API is running.
    """
    return {"status": "API is running"}