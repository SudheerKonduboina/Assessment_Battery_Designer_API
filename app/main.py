import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI
from .api import chat
from .core.agent import Agent
import os

app = FastAPI(title="SHL Recommender", version="8.5")

@app.on_event("startup")
async def startup_event():
    catalog_path = os.path.join(os.path.dirname(__file__), "data", "shl_product_catalogue.json")
    chat.agent = Agent(catalog_path)
    
    # Safely load the model in the background so uvicorn binds port quickly
    import asyncio
    from .core.ranker import get_model
    asyncio.create_task(asyncio.to_thread(get_model))
    
    print("=== SHL SYSTEM READY (v8.5) ===")

# STRICT HEALTH CONTRACT (MANDATORY)
@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(chat.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
