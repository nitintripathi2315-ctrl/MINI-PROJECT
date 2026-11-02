"""
FastAPI server for the Restaurant Order Agent.

Run locally:  uvicorn server:app --reload --port 8000
Env vars:     GROQ_API_KEY, GROQ_MODEL (default openai/gpt-oss-120b),
              ALLOWED_ORIGINS (comma separated, default "*"),
              FAKE_LLM=1 (use the offline keyword brain, no API key needed)
"""
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from agent import MENU, GroqBrain, ScriptedBrain, build_graph, initial_state

load_dotenv()


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=300)


def create_app(brain=None, cook_ok=None, serve_ok=None) -> FastAPI:
    app = FastAPI(title="Restaurant Order Agent")

    origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    if brain is None:
        brain = ScriptedBrain() if os.environ.get("FAKE_LLM") == "1" else GroqBrain()

    kwargs = {}
    if cook_ok:
        kwargs["cook_ok"] = cook_ok
    if serve_ok:
        kwargs["serve_ok"] = serve_ok

    # input_fn=None -> get_input pauses with interrupt(); MemorySaver remembers each session (thread_id)
    graph = build_graph(brain, input_fn=None, out=lambda s: None, checkpointer=MemorySaver(), **kwargs)

    def snapshot(config, before_msgs: int, before_log: int) -> dict:
        st = graph.get_state(config)
        v = st.values
        return {
            "replies": [m.content for m in v["messages"][before_msgs:] if m.type == "ai"],
            "events": v["log"][before_log:],
            "status": v["status"],
            "order": {"dish": v["dish_name"], "required_qty": v["required_qty"],
                      "available_qty": v["available_qty"]},
            "retries": {"order": v["order_retries"], "cook": v["cook_retries"], "serve": v["serve_retries"]},
            "done": not st.next,                       # True when the graph reached END
            "final_result": v["final_result"] or None,  # "COMPLETED" / "FAILED" / None
        }

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/menu")
    def menu():
        return {"menu": MENU}

    @app.post("/api/start")
    def start():
        """Create a new session; runs greet -> get_input and pauses waiting for the user."""
        session_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}
        try:
            graph.invoke(initial_state(), config)
        except Exception as e:  # e.g. LLM provider error
            raise HTTPException(502, f"Agent error: {type(e).__name__}")
        return {"session_id": session_id, **snapshot(config, 0, 0)}

    @app.post("/api/chat")
    def chat(req: ChatRequest):
        config = {"configurable": {"thread_id": req.session_id}, "recursion_limit": 100}
        st = graph.get_state(config)
        if not st.values:
            raise HTTPException(404, "Unknown session. Start a new order.")
        if not st.next:
            raise HTTPException(409, "This order is finished. Start a new order.")
        before_msgs, before_log = len(st.values["messages"]), len(st.values["log"])
        try:
            graph.invoke(Command(resume=req.message), config)
        except Exception as e:
            raise HTTPException(502, f"Agent error: {type(e).__name__}")
        return {"session_id": req.session_id, **snapshot(config, before_msgs, before_log)}

    return app


app = create_app()