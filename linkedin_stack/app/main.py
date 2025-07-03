from fastapi import FastAPI, Depends, status, HTTPException, BackgroundTasks
from typing import List, Dict
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from . import models, auth
from .services import (
    supabase_service,
    pinecone_service,
    generation_service,
    scraper_service,
    post_service
)
from supabase import Client

app = FastAPI(
    title="LinkedIn Post Generation Service",
    description="A service to generate LinkedIn posts for users.",
    version="1.0.0"
)

# In-memory store for job statuses
tasks: Dict[str, models.JobStatus] = {}

async def run_manual_generation_task(
    task_id: str,
    user_id: str,
    request: models.ManualGenerateRequest,
    supabase: Client
):
    """The actual logic for generating a post, run in the background."""
    try:
        # Log the start of the task
        logging.info(f"Starting manual generation task {task_id} for user {user_id} on topic: {request.topic}")
        
        # await supabase_service.check_post_limit(user_id, supabase)
        # logging.info(f"Checked post limit for user {user_id}")
        
        # job_id = await scraper_service.start_topic_scrape(user_id, request.topic)
        job_id = "placeholder_job_id" # Bypassing scraper for testing
        logging.info(f"Bypassed scrape job for topic {request.topic}")
        
        context = await pinecone_service.get_context_for_manual_post(user_id, request.topic, job_id)
        logging.info(f"Retrieved context for manual post generation. Context length: {len(context) if context else 0}")
        
        user_style = await supabase_service.get_user_style(user_id, supabase)
        logging.info(f"Retrieved user style for user {user_id}")
        
        post_content = await generation_service.generate(
            context=context,
            style=user_style,
            topic=request.topic,
            length=request.length,
            instructions=request.additional_instructions
        )
        logging.info(f"Generated post content for topic {request.topic}")
        
        # Save the generated post
        saved_post = await post_service.create_post(
            user_id=user_id,
            post_data=models.PostCreate(content=post_content),
            supabase=supabase
        )
        logging.info(f"Saved post with ID {saved_post['id']}")
        
        # await supabase_service.increment_post_count(user_id, supabase)
        # logging.info(f"Incremented post count for user {user_id}")
        
        # Update task status to completed
        tasks[task_id].status = "completed"
        tasks[task_id].result = models.JobResult(post_id=saved_post['id'], content=saved_post['content'])
        logging.info(f"Task {task_id} completed successfully.")
        
    except Exception as e:
        logging.error(f"Task {task_id} failed: {str(e)}", exc_info=True)
        # Update task status to failed
        tasks[task_id].status = "failed"
        tasks[task_id].result = models.JobResult(error=str(e))
        logging.info(f"Task {task_id} marked as failed.")

# --- Generation Endpoints ---

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/generate/auto", response_model=models.GeneratedPost)
async def auto_generate_post(
    request: models.AutoGenerateRequest, user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)
):
    """Generates a LinkedIn post based on the user's onboarding profile."""
    # This remains synchronous as it's assumed to be faster
    # await supabase_service.check_post_limit(user_id, supabase)
    context = await pinecone_service.get_context_for_auto_post(user_id, supabase)
    user_style = await supabase_service.get_user_style(user_id, supabase)
    post_content = await generation_service.generate(
        context=context,
        style=user_style,
        length=request.length,
        instructions=request.additional_instructions
    )
    # await supabase_service.increment_post_count(user_id, supabase)
    return models.GeneratedPost(content=post_content)

@app.post("/generate/manual", response_model=models.JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def manual_generate_post(
    request: models.ManualGenerateRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(auth.get_user_id_from_token),
    supabase: Client = Depends(auth.get_supabase_client)
):
    """Accepts a request to generate a post and returns a task ID."""
    task_id = str(uuid.uuid4())
    tasks[task_id] = models.JobStatus(task_id=task_id, status="pending")
    background_tasks.add_task(run_manual_generation_task, task_id, user_id, request, supabase)
    return models.JobResponse(task_id=task_id)

@app.get("/generate/status/{task_id}", response_model=models.JobStatus)
async def get_generation_status(task_id: str):
    """Retrieves the status and result of a generation task."""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return task

# --- Post Management Endpoints ---

@app.post("/posts", response_model=models.Post, status_code=status.HTTP_201_CREATED)
async def save_post(
    post_data: models.PostCreate, user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)
):
    """Saves a generated post to the database."""
    return await post_service.create_post(user_id, post_data, supabase)

@app.get("/posts", response_model=List[models.Post])
async def list_posts(user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)):
    """Lists all saved posts for the current user."""
    return await post_service.get_posts(user_id, supabase)

@app.get("/posts/{post_id}", response_model=models.Post)
async def get_single_post(post_id: str, user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)):
    """Retrieves a single post by its ID."""
    return await post_service.get_post(user_id, post_id, supabase)

@app.put("/posts/{post_id}", response_model=models.Post)
async def edit_post(post_id: str, post_data: models.PostUpdate, user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)):
    """Updates a specific post."""
    return await post_service.update_post(user_id, post_id, post_data, supabase)

@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_post(post_id: str, user_id: str = Depends(auth.get_user_id_from_token), supabase: Client = Depends(auth.get_supabase_client)):
    """Deletes a specific post."""
    await post_service.delete_post(user_id, post_id, supabase)

@app.get("/test-auth")
async def test_auth(supabase: Client = Depends(auth.get_supabase_client)):
    """Test endpoint to validate Supabase authentication."""
    try:
        # Try to get the current user
        user_response = supabase.auth.get_user()
        print(f"--- Supabase get_user response: {user_response} ---")
        if user_response and user_response.user:
            return {"status": "success", "user_id": user_response.user.id}
        else:
            print(f"--- Supabase get_user returned no user: {user_response} ---")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Supabase authentication returned no user"
            )
    except Exception as e:
        print(f"--- Exception in test_auth: {e} ---")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication test failed: {str(e)}"
        )
