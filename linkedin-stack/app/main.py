# from fastapi import FastAPI, Depends, status, HTTPException
from typing import List, Dict
import logging

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ Absolute Imports (important for AWS Lambda)
from app import models, auth
from app.services import (
    supabase_service,
    pinecone_service,
    generation_service,
    scraper_service,
    post_service
)
from supabase import Client

app = FastAPI(
    title="LinkedIn Post Generation Service",
    description="Generates personalized LinkedIn posts for users.",
    version="1.0.0"
)

# ---------------------------
# Routes
# ---------------------------

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/generate/auto", response_model=models.GeneratedPost)
async def auto_generate_post(
    request: models.AutoGenerateRequest,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    context = await pinecone_service.get_context_for_auto_post(user_id, supabase)
    user_style = await supabase_service.get_user_style(user_id, supabase)
    post_content = await generation_service.generate(
        context=context,
        style=user_style,
        length=request.length,
        instructions=request.additional_instructions
    )
    return models.GeneratedPost(content=post_content)

@app.post("/generate/manual", response_model=models.GeneratedPost)
async def manual_generate_post(
    request: models.ManualGenerateRequest,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    try:
        logger.info(f"Manual generation started for user {user_id} with topic: {request.topic}")

        context = await pinecone_service.get_context_for_manual_post(user_id, request.topic)
        user_style = await supabase_service.get_user_style(user_id, supabase)

        post_content = await generation_service.generate(
            context=context,
            style=user_style,
            topic=request.topic,
            length=request.length,
            instructions=request.additional_instructions
        )

        await post_service.create_post(
            user_id=user_id,
            post_data=models.PostCreate(content=post_content),
            supabase=supabase
        )

        logger.info(f"Manual generation for user {user_id} completed successfully.")
        return models.GeneratedPost(content=post_content)

    except Exception as e:
        logger.error(f"Error during manual generation for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/posts", response_model=models.Post, status_code=status.HTTP_201_CREATED)
async def save_post(
    post_data: models.PostCreate,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    return await post_service.create_post(user_id, post_data, supabase)

@app.get("/posts", response_model=List[models.Post])
async def list_posts(
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    return await post_service.get_posts(user_id, supabase)

@app.get("/posts/{post_id}", response_model=models.Post)
async def get_single_post(
    post_id: str,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    return await post_service.get_post(user_id, post_id, supabase)

@app.put("/posts/{post_id}", response_model=models.Post)
async def edit_post(
    post_id: str,
    post_data: models.PostUpdate,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    return await post_service.update_post(user_id, post_id, post_data, supabase)

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_post(
    post_id: str,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    await post_service.delete_post(user_id, post_id, supabase)

@app.get("/test-auth")
async def test_auth(supabase: Client = Depends(auth.get_supabase_client)):
    try:
        user_response = supabase.auth.get_user()
        if user_response and user_response.user:
            return {"status": "success", "user_id": user_response.user.id}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Auth failed: {str(e)}")

# ---------------------------
# AWS Lambda Adapter
# ---------------------------
try:
    from mangum import Mangum
    lambda_handler = Mangum(app)
except ImportError:
    lambda_handler = None
