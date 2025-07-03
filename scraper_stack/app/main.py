import uuid
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse

app = FastAPI(title="Scraper Service")

class ScrapeRequest(BaseModel):
    user_id: str
    topic: str

@app.get("/")
def read_root():
    return {"message": "Scraper Service is running."}

@app.post("/scrape/topic", response_class=JSONResponse)
async def scrape_topic(request: ScrapeRequest):
    """
    This is a placeholder for the actual scraper service.
    It simulates starting a scraping job and returns a job_id.
    """
    print(f"--- SCRAPER: Received request to scrape topic '{request.topic}' for user '{request.user_id}' ---")
    
    job_id = str(uuid.uuid4())
    
    print(f"--- SCRAPER: Started job with ID: {job_id} ---")
    
    # The linkedin_stack service expects a JSON response with a 'job_id' key.
    return {"job_id": job_id}
