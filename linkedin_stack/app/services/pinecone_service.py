import logging
from pinecone import Pinecone, EmbedModel
from supabase import Client
from .. import config
from . import supabase_service
from fastapi import HTTPException

logging.basicConfig(level=logging.INFO)

# --- Pinecone Initialization ---
try:
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    pc_index = pc.Index(config.PINECONE_INDEX_NAME)
except Exception as e:
    logging.error(f"Could not initialize Pinecone: {e}")
    pc_index = None

async def get_context_for_auto_post(user_id: str, supabase: Client) -> str:
    """Retrieves context from Pinecone using the user's initial profile scrape."""
    if not pc_index:
        logging.error("Pinecone index is not available.")
        raise HTTPException(status_code=503, detail="Content generation service is currently unavailable.")

    try:
        logging.info(f"[{user_id}] Fetching profile text from Supabase for auto-post context.")
        profile_text = await supabase_service.get_profile_for_embedding(user_id, supabase)
        if not profile_text:
            logging.warning(f"[{user_id}] No profile text found in Supabase. Cannot query Pinecone.")
            return "" # Return empty context if no profile text is available.

        logging.info(f"[{user_id}] Generating query embedding for auto-post.")
        query_embeddings_response = pc.inference.embed(
            model=EmbedModel.Multilingual_E5_Large, 
            inputs=[profile_text],
            parameters={"input_type": "query"}
        )
        if not query_embeddings_response.data or not query_embeddings_response.data[0].values:
            logging.error(f"[{user_id}] Failed to generate query embedding for auto-post. Response from embedding model was empty.")
            raise HTTPException(status_code=500, detail="Failed to generate content embedding.")

        query_embedding = query_embeddings_response.data[0].values
        logging.info(f"[{user_id}] Successfully generated query embedding for auto-post.")

        logging.info(f"[{user_id}] Querying Pinecone for auto-post context.")
        query_response = pc_index.query(
            vector=query_embedding,
            top_k=5,
            namespace=user_id,
            filter={"source_type": "profile"},
            include_metadata=True
        )
        logging.info(f"[{user_id}] Pinecone query successful. Found {len(query_response['matches'])} matches.")
        
        if not query_response['matches']:
            logging.warning(f"[{user_id}] No context found in Pinecone for auto-post (source_type='profile').")
            return ""

        context = " ".join([match['metadata']['text'] for match in query_response['matches']])
        logging.info(f"[{user_id}] Successfully retrieved and processed context for auto-post.")
        return context
    except Exception as e:
        logging.error(f"[{user_id}] Error querying Pinecone for auto post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to query context from Pinecone.")

async def get_context_for_manual_post(user_id: str, topic: str, job_id: str) -> str:
    """
    Retrieves context for a manual post with detailed, multi-stage debugging.
    """
    if not pc_index:
        logging.error("Pinecone index is not available.")
        raise HTTPException(status_code=503, detail="Content generation service is currently unavailable.")

    # Stage 1: Embedding Generation
    try:
        logging.info(f"[{user_id}] [Debug] Stage 1: Generating embedding for topic: '{topic}'.")
        query_embeddings_response = pc.inference.embed(
            model=EmbedModel.Multilingual_E5_Large,
            inputs=[topic],
            parameters={"input_type": "query"}
        )
        # This is the key change: log the full response if it's not what we expect.
        if not query_embeddings_response.data or not query_embeddings_response.data[0].values:
            logging.error(f"[{user_id}] [Debug] Embedding response was empty. Full response from Pinecone: {query_embeddings_response}")
            raise HTTPException(status_code=500, detail="[Debug] Stage 1 Failed: Embedding response was empty. Check terminal logs for details.")
        query_embedding = query_embeddings_response.data[0].values
        logging.info(f"[{user_id}] [Debug] Stage 1 Succeeded.")
    except Exception as e:
        logging.error(f"[{user_id}] [Debug] Exception during Stage 1 (Embedding Generation): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"[Debug] Stage 1 Failed: {e}")

    # Stage 2: Pinecone Query
    try:
        logging.info(f"[{user_id}] [Debug] Stage 2: Querying Pinecone with namespace '{user_id}'.")
        query_response = pc_index.query(
            vector=query_embedding,
            top_k=5,
            namespace=user_id,
            filter={"source_type": "profile"},
            include_metadata=True
        )
        logging.info(f"[{user_id}] [Debug] Stage 2 Succeeded. Found {len(query_response.get('matches', []))} matches.")
    except Exception as e:
        logging.error(f"[{user_id}] [Debug] Exception during Stage 2 (Pinecone Query): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"[Debug] Stage 2 Failed: {e}")

    # Stage 3: Context Processing
    try:
        logging.info(f"[{user_id}] [Debug] Stage 3: Processing query response.")
        if not query_response.get('matches'):
            logging.warning(f"[{user_id}] [Debug] No context found in Pinecone for topic '{topic}'. Using topic as context.")
            return topic
        context = " ".join([match['metadata']['text'] for match in query_response['matches']])
        logging.info(f"[{user_id}] [Debug] Stage 3 Succeeded. Context retrieved.")
        return context
    except Exception as e:
        logging.error(f"[{user_id}] [Debug] Exception during Stage 3 (Context Processing): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"[Debug] Stage 3 Failed: {e}")
