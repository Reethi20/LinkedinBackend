from supabase import Client
from .. import config
import datetime
from fastapi import HTTPException, status

POST_LIMIT_PER_DAY = 25

async def get_profile_for_embedding(user_id: str, supabase: Client) -> str:
    """Fetches the user's core profile answers for generating an embedding."""
    try:
        response = supabase.table('onboarding').select('question1, question2, question3').eq('user_id', user_id).single().execute()
        if response.data:
            return f"Product/Service: {response.data.get('question1', '')}. Ideal Customers: {response.data.get('question2', '')}. Problem Solved: {response.data.get('question3', '')}."
        raise HTTPException(status_code=404, detail="Onboarding data not found for user.")
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail="Could not fetch user profile data.")

async def get_user_style(user_id: str, supabase: Client) -> str:
    """Fetches the user's unique style from the onboarding table."""
    try:
        response = supabase.table('onboarding').select('question4').eq('user_id', user_id).single().execute()
        if response.data and 'question4' in response.data:
            return response.data['question4']
        return "professional" # Default style
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail="Could not fetch user style.")

async def check_post_limit(user_id: str, supabase: Client):
    """Checks if the user has exceeded their daily post limit."""
    today = datetime.date.today().isoformat()
    try:
        response = supabase.table('daily_post_counts').select('post_count').eq('user_id', user_id).eq('date', today).single().execute()
        if response.data and response.data['post_count'] >= POST_LIMIT_PER_DAY:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily post limit reached.")
    except Exception as e:
        # This will also catch the case where no row exists for the user today, which is fine.
        pass

async def get_brand_profile_topic(user_id: str, supabase: Client) -> str:
    """Fetches the user's brand profile topic (answer to question3) from the onboarding table."""
    try:
        response = supabase.table('onboarding').select('question3').eq('user_id', user_id).single().execute()
        if response.data and 'question3' in response.data:
            return response.data['question3']
        # If not found, this is a critical error in data integrity.
        raise HTTPException(status_code=404, detail="Brand profile topic not found for user.")
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail="Could not fetch brand profile topic.")

async def increment_post_count(user_id: str, supabase: Client):
    """Increments the user's post count for the day using a database function."""
    try:
        supabase.rpc('increment_post_count', {'user_id_param': user_id}).execute()
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail="Could not update post count.")
