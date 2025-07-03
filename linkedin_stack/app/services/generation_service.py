import logging
from fastapi import HTTPException
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from .. import config

# --- 1. Define Graph State ---
class GenerationState(TypedDict):
    # Inputs
    context: str
    style: str
    topic: str
    length: str
    instructions: str
    # Intermediate state
    prompt: str
    # Output
    generated_post: str

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 2. Initialize the LLM ---
# This will be used in our graph to generate the post.
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=config.GOOGLE_API_KEY, temperature=0.7)
except Exception as e:
    print(f"Failed to initialize Google Gemini LLM: {e}")
    llm = None

# --- 3. Define Graph Nodes ---
def build_prompt(state: GenerationState) -> GenerationState:
    """Constructs the final prompt for the LLM from the input state."""
    print("--- Node: build_prompt ---")
    system_prompt = (
        f"You are an expert B2B social media marketer specializing in LinkedIn. "
        f"Your task is to write a compelling LinkedIn post based on the provided context and instructions. "
        f"The post must be written in a {state['style']} tone and should be approximately {state['length']} in length."
    )

    user_prompt = (
        f"**Background Context:**\n{state['context']}\n\n"
        f"**Task:**\n"
        f"Please write a LinkedIn post.\n"
        f"- **Topic:** {state['topic'] if state['topic'] else 'General post based on my profile.'}\n"
        f"- **Additional Instructions:** {state['instructions'] if state['instructions'] else 'None'}"
    )
    
    state['prompt'] = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    return state

def generate_post_node(state: GenerationState) -> GenerationState:
    """Calls the LLM to generate the LinkedIn post."""
    logger.info("--- [LLM] Node: generate_post_node ---")
    if not llm:
        raise Exception("LLM service is not available. Check API Key.")

    try:
        logger.info("--- [LLM] Invoking language model... ---")
        response = llm.invoke(state['prompt'])
        logger.info("--- [LLM] Successfully received response from language model. ---")
        state['generated_post'] = response.content
        return state
    except Exception as e:
        logger.error(f"--- [LLM] Exception during LLM invocation: {e} ---", exc_info=True)
        # Re-raise with a more descriptive message
        raise Exception(f"LLM invocation failed. Raw error: {e}")

# --- 4. Build and Compile the Graph ---
workflow = StateGraph(GenerationState)
workflow.add_node("build_prompt", build_prompt)
workflow.add_node("generate_post", generate_post_node)

workflow.set_entry_point("build_prompt")
workflow.add_edge("build_prompt", "generate_post")
workflow.add_edge("generate_post", END)

app_graph = workflow.compile()

# --- 5. Main Service Function ---
async def generate(
    context: str,
    style: str,
    topic: str = None,
    length: str = "medium",
    instructions: str = ""
) -> str:
    """Generates a LinkedIn post using the LangGraph chain."""
    try:
        inputs = {
            "context": context,
            "style": style,
            "topic": topic,
            "length": length,
            "instructions": instructions
        }
        final_state = app_graph.invoke(inputs)
        return final_state.get("generated_post", "Error: Could not generate post.")
    except Exception as e:
        logger.error(f"--- [LLM] Error during graph invocation: {e} ---", exc_info=True)
        # The detail now includes the specific error from the graph
        raise HTTPException(status_code=500, detail=str(e))
