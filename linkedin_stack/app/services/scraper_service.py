import httpx
from fastapi import HTTPException
from .. import config
import uuid

# In a real-world scenario, you would use a more robust client
client = httpx.AsyncClient()

async def start_topic_scrape(user_id: str, topic: str) -> str:
    """Triggers the scraper service to start a new job for a given topic."""
    # This is a placeholder. In reality, you would make a call to the scraper service.
    # The scraper service would then do its work and you might poll for completion
    # or use a webhook. For now, we'll simulate the call and return a fake job_id.

    scraper_url = f"{config.SCRAPER_SERVICE_URL}/scrape/topic"
    print(f"--- Calling Scraper Service at: {scraper_url} ---")
    print(f"--- Payload: user_id={user_id}, topic={topic} ---")

    try:
        response = await client.post(scraper_url, json={"user_id": user_id, "topic": topic}, timeout=30.0)
        response.raise_for_status() # Raise an exception for 4xx or 5xx status codes
        job_id = response.json().get("job_id")
        if not job_id:
            raise HTTPException(status_code=500, detail="Scraper service did not return a job_id.")
        return job_id
    except httpx.RequestError as e:
        # Log the exception e
        raise HTTPException(status_code=503, detail=f"Could not connect to the scraper service: {e}")
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"An error occurred with the scraper service: {e}")
