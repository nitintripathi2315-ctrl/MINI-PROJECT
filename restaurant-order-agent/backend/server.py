"""
FastAPI server for the Restaurant Order Agent (with streaming).

Run locally:  uvicorn server:app --reload --port 8000
Env vars:     GROQ_API_KEY, GROQ_MODEL (default openai/gpt-oss-120b),
              ALLOWED_ORIGINS (comma separated, default "*"),
              STEP_DELAY (seconds of kitchen/waiter pause per step, default 0.8; 0 = instant),
              FAKE_LLM=1 (use the offline keyword brain, no API key needed)

Endpoints:
  GET  /health, /api/menu
  POST /api/start, /api/chat                 normal JSON responses (kept for tests / simple clients)
  POST /api/start/stream, /api/chat/stream   Server-Sent Events: each step is sent as soon as it happens
"""
import json
import os
import random
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from agent import MENU, GroqBrain, ScriptedBrain, build_graph, initial_state

load_dotenv()


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=300)


def sse(event: str, data: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def create_app(brain=None, cook_ok=None, serve_ok=None) -> FastAPI:
    app = FastAPI(title="Restaurant Order Agent")

    origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

    if brain is None:
        brain = ScriptedBrain() if os.environ.get("FAKE_LLM") == "1" else GroqBrain()

    # kitchen/waiter steps pause briefly so the live progress is visible in the UI
    delay = float(os.environ.get("STEP_DELAY", "0.8"))

    def paced(fn):
        def wrapper():
            if delay > 0:
                time.sleep(delay)
            return fn()
        return wrapper

    base_cook = cook_ok or (lambda: random.random() < 0.60)
    base_serve = serve_ok or (lambda: random.random() < 0.60)

    # input_fn=None -> get_input pauses with interrupt(); MemorySaver remembers each session (thread_id)
    graph = build_graph(brain, input_fn=None, out=lambda s: None, checkpointer=MemorySaver(),
                        cook_ok=paced(base_cook), serve_ok=paced(base_serve))

    def view(config) -> dict:
        st = graph.get_state(config)
        v = st.values
        return {
            "status": v["status"],
            "order": {"dish": v["dish_name"], "required_qty": v["required_qty"],
                      "available_qty": v["available_qty"]},
            "retries": {"order": v["order_retries"], "cook": v["cook_retries"], "serve": v["serve_retries"]},
            "done": not st.next,                       # True when the graph reached END
            "final_result": v["final_result"] or None,  # "COMPLETED" / "FAILED" / None
        }

    def snapshot(config, before_msgs: int, before_log: int) -> dict:
        v = graph.get_state(config).values
        return {
            "replies": [m.content for m in v["messages"][before_msgs:] if m.type == "ai"],
            "events": v["log"][before_log:],
            **view(config),
        }

    def stream_run(graph_input, config):
        """Run the graph and yield SSE events as each node finishes."""
        try:
            for chunk in graph.stream(graph_input, config, stream_mode="updates"):
                for node, update in chunk.items():
                    if node.startswith("__") or not isinstance(update, dict):
                        continue  # e.g. __interrupt__ (graph paused, waiting for the user)
                    for m in update.get("messages", []):
                        if m.type == "ai":
                            yield sse("reply", {"text": m.content})
                    for line in update.get("log", []):
                        yield sse("event", {"text": line})
            yield sse("state", view(config))
        except Exception as e:
            yield sse("error", {"detail": f"Agent error: {type(e).__name__}"})

    def streaming_response(gen):
        return StreamingResponse(gen, media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def checked_config(session_id: str):
        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}
        st = graph.get_state(config)
        if not st.values:
            raise HTTPException(404, "Unknown session. Start a new order.")
        if not st.next:
            raise HTTPException(409, "This order is finished. Start a new order.")
        return config

    # ---- basic endpoints -------------------------------------------------
    @app.get("/health")
    def health():
        return {"ok": True}

    @app.get("/api/menu")
    def menu():
        return {"menu": MENU}

    # ---- normal JSON endpoints -----------------------------------------------
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
        config = checked_config(req.session_id)
        st = graph.get_state(config)
        before_msgs, before_log = len(st.values["messages"]), len(st.values["log"])
        try:
            graph.invoke(Command(resume=req.message), config)
        except Exception as e:
            raise HTTPException(502, f"Agent error: {type(e).__name__}")
        return {"session_id": req.session_id, **snapshot(config, before_msgs, before_log)}

    # ---- streaming endpoints (Server-Sent Events) ------------------------------
    @app.post("/api/start/stream")
    def start_stream():
        session_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}

        def gen():
            yield sse("session", {"session_id": session_id})
            yield from stream_run(initial_state(), config)

        return streaming_response(gen())

    @app.post("/api/chat/stream")
    def chat_stream(req: ChatRequest):
        config = checked_config(req.session_id)   # 404 / 409 are raised before streaming starts
        return streaming_response(stream_run(Command(resume=req.message), config))

    return app


app = create_app()
