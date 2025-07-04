from supabase import Client
from .. import models
from fastapi import HTTPException, status
import datetime

async def create_post(user_id: str, post_data: models.PostCreate, supabase: Client) -> dict:
    """Saves a new post to the database."""
    try:
        response = supabase.table('linkedin_posts').insert({
            'user_id': user_id,
            'content': post_data.content,
            'status': 'draft' # Default status
        }).execute()

        if response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to save post.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

async def get_posts(user_id: str, supabase: Client) -> list[dict]:
    """Retrieves all posts for a given user."""
    try:
        response = supabase.table('linkedin_posts').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

async def get_post(user_id: str, post_id: str, supabase: Client) -> dict:
    """Retrieves a single post by its ID, ensuring user ownership."""
    try:
        response = supabase.table('linkedin_posts').select('*').eq('id', post_id).eq('user_id', user_id).single().execute()
        if response.data:
            return response.data
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

async def update_post(user_id: str, post_id: str, post_data: models.PostUpdate, supabase: Client) -> dict:
    """Updates the content of a specific post."""
    # First, verify the post exists and belongs to the user
    await get_post(user_id, post_id, supabase)
    
    try:
        response = supabase.table('linkedin_posts').update({
            'content': post_data.content,
            'updated_at': datetime.datetime.now().isoformat()
        }).eq('id', post_id).execute()

        if response.data:
            return response.data[0]
        raise HTTPException(status_code=500, detail="Failed to update post.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

async def delete_post(user_id: str, post_id: str, supabase: Client):
    """Deletes a specific post."""
    # First, verify the post exists and belongs to the user
    await get_post(user_id, post_id, supabase)
    
    try:
        supabase.table('linkedin_posts').delete().eq('id', post_id).execute()
        return
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
