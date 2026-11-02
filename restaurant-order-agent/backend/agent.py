"""
Restaurant Order Management Agent (LangGraph)

Core agent (used by both the CLI and the FastAPI web server in main.py).
CLI live:   python agent.py          (needs GROQ_API_KEY)
CLI tests:  python agent.py --test   (no API key needed)
"""
import operator
import os
import random
import re
import sys
from typing import Annotated, Callable, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

# --------------------------------------------------------------------------
# MENU (PLACEHOLDER - replace with your real menu): dish -> available quantity
# --------------------------------------------------------------------------
MENU = {"pizza": 5, "burger": 3, "pasta": 10, "sushi": 0}


# --------------------------------------------------------------------------
# STATE
# --------------------------------------------------------------------------
class OrderState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    dish_name: str
    required_qty: int
    available_qty: int        # written by order_confirm (0 if dish not on menu)
    status: str               # see STATUS values below
    order_retries: int        # starts 3
    cook_retries: int         # starts 2
    serve_retries: int        # starts 2
    final_result: str         # "COMPLETED" or "FAILED"
    end_reason: str
    log: Annotated[list[str], operator.add]   # kitchen events shown in the web UI


# status values: start | unrelated | confirmed | partial | not_available |
#                ready | cook_failed | serve_failed | complete | failed


def initial_state() -> OrderState:
    return {
        "messages": [], "dish_name": "", "required_qty": 0, "available_qty": 0,
        "status": "start", "order_retries": 3, "cook_retries": 2,
        "serve_retries": 2, "final_result": "", "end_reason": "", "log": [],
    }


# --------------------------------------------------------------------------
# "BRAINS": the LLM part. Two jobs: (1) parse user text, (2) write messages.
# --------------------------------------------------------------------------
class GroqBrain:
    def __init__(self, model: str = None):
        from langchain_groq import ChatGroq
        model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        from pydantic import BaseModel, Field

        class Intent(BaseModel):
            intent: str = Field(description="one of: order, confirm_partial, reject, unrelated")
            dish: Optional[str] = Field(default=None, description="lowercase dish name if intent=order")
            quantity: Optional[int] = Field(default=None, description="quantity if intent=order, default 1")

        self.llm = ChatGroq(model=model, temperature=0)
        self.parser = self.llm.with_structured_output(Intent)

    def parse(self, text: str, awaiting_partial_confirm: bool) -> dict:
        ctx = ("The agent just offered a PARTIAL order; the user may confirm it (confirm_partial), "
               "reject it (reject), or place a new order (order). " if awaiting_partial_confirm else "")
        prompt = (
            "You are the input parser of a restaurant FOOD ORDERING agent. " + ctx +
            "Classify the user message. intent=order if they order a dish (extract ONE dish and quantity). "
            "intent=unrelated for anything not about food ordering.\nUser: " + text
        )
        r = self.parser.invoke(prompt)
        return {"intent": r.intent, "dish": (r.dish or "").lower().strip(), "qty": r.quantity or 1}

    def say(self, situation: str) -> str:
        """Phrase a fixed fact as a message TO the customer. The facts come from the graph state;
        the LLM only rewords them and is not allowed to add anything."""
        sys = (
            "You are the voice of a restaurant FOOD-ORDERING AI agent, speaking TO the customer. "
            "The user message contains a FACT. Rewrite that fact as a short, friendly message "
            "(1-2 sentences) addressed to the customer. Keep every dish name, number and instruction exactly. "
            "NEVER speak as the customer, never place an order yourself, and never invent anything "
            "(no order numbers, prices, dishes or extra questions). Output only the message."
        )
        try:
            text = (self.llm.invoke([("system", sys), ("human", "FACT: " + situation)]).content or "").strip()
        except Exception:
            return situation
        # guard: the numbers in the reply must match the fact exactly, else use the plain fact
        if not text or set(re.findall(r"\d+", text)) != set(re.findall(r"\d+", situation)):
            return situation
        return text


class ScriptedBrain:
    """Offline stand-in for the LLM so tests are deterministic."""

    def parse(self, text: str, awaiting_partial_confirm: bool) -> dict:
        t = text.lower().strip()
        if awaiting_partial_confirm and re.match(r"(yes|confirm|ok|go ahead)", t):
            return {"intent": "confirm_partial", "dish": "", "qty": 0}
        m = re.search(r"order\s+(\d+)\s+([a-z ]+)", t)
        if m:
            return {"intent": "order", "dish": m.group(2).strip(), "qty": int(m.group(1))}
        if re.match(r"(no|reject|cancel)", t):
            return {"intent": "reject", "dish": "", "qty": 0}
        return {"intent": "unrelated", "dish": "", "qty": 0}

    def say(self, situation: str) -> str:
        return situation


# --------------------------------------------------------------------------
# GRAPH BUILDER
# --------------------------------------------------------------------------
def build_graph(
    brain,
    input_fn: Optional[Callable[[], str]] = None,   # None -> pause with interrupt() (web mode)
    cook_ok: Callable[[], bool] = lambda: random.random() < 0.60,   # 60% success
    serve_ok: Callable[[], bool] = lambda: random.random() < 0.60,  # assumed 60%
    menu: dict = MENU,
    out: Callable[[str], None] = print,
    checkpointer=None,
):
    def speak(situation: str) -> AIMessage:
        text = brain.say(situation)
        out(f"AI : {text}")
        return AIMessage(content=text)

    # ---- nodes ----------------------------------------------------------
    def greet(state):
        return {"messages": [speak("Welcome! What would you like to order? (one dish and quantity)")]}

    def get_input(state):
        if input_fn is None:
            text = interrupt({"awaiting": "user_input"})   # graph pauses here until resumed
        else:
            text = input_fn()
        return {"messages": [HumanMessage(content=text)]}

    def understand(state):
        """LLM extracts dish + quantity, or detects unrelated / confirm / reject."""
        text = state["messages"][-1].content
        awaiting = state["status"] == "partial"
        r = brain.parse(text, awaiting)
        intent = r["intent"]

        if intent == "confirm_partial" and awaiting:
            msg = speak(f"Great, proceeding with the partial order of {state['available_qty']} {state['dish_name']}.")
            return {"required_qty": state["available_qty"], "status": "confirmed", "messages": [msg]}

        if intent == "order" and r["dish"]:
            return {"dish_name": r["dish"], "required_qty": max(1, r["qty"]), "status": "start"}

        if intent == "reject":
            msg = speak("No problem. Please tell me a new dish and quantity.")
            return {"status": "start", "messages": [msg]}

        # unrelated input: refuse and count it as a used order attempt
        left = state["order_retries"] - 1
        msg = speak("I'm an AI agent for restaurant food ordering, not a general purpose assistant. "
                    "Please tell me a dish and quantity.")
        return {"status": "unrelated", "order_retries": left, "messages": [msg]}

    def order_confirm(state):
        dish, req = state["dish_name"], state["required_qty"]
        avail = menu.get(dish, 0)  # not on menu -> 0
        if avail >= req and avail > 0:
            msg = speak(f"Your order of {req} {dish} is available. Sending to the kitchen.")
            return {"available_qty": avail, "status": "confirmed", "messages": [msg]}
        left = state["order_retries"] - 1
        if avail > 0:
            msg = speak(f"Only {avail} {dish} available (you asked for {req}). "
                        f"Confirm the partial order of {avail}, or place a new order.")
            return {"available_qty": avail, "status": "partial", "order_retries": left, "messages": [msg]}
        msg = speak(f"Sorry, {dish} is not available. Please place a new order.")
        return {"available_qty": 0, "status": "not_available", "order_retries": left, "messages": [msg]}

    def cook(state):
        if cook_ok():
            out("[cook] success -> READY")
            return {"status": "ready", "log": ["Kitchen: dish cooked successfully"]}
        left = state["cook_retries"] - 1
        out(f"[cook] FAILED (cook retries left: {left})")
        return {"status": "cook_failed", "cook_retries": left,
                "log": [f"Kitchen: cooking failed (cook retries left: {left})"]}

    def serve(state):
        if serve_ok():
            out("[serve] success -> COMPLETE")
            return {"status": "complete", "log": ["Waiter: order served successfully"]}
        left = state["serve_retries"] - 1
        out(f"[serve] FAILED (serve retries left: {left})")
        return {"status": "serve_failed", "serve_retries": left,
                "log": [f"Waiter: serving failed (serve retries left: {left})"]}

    def finish_success(state):
        msg = speak(f"Your order of {state['required_qty']} {state['dish_name']} is complete. Enjoy your meal!")
        return {"final_result": "COMPLETED", "status": "complete", "messages": [msg]}

    def finish_fail(state):
        reasons = {
            "order": "we couldn't find an order that works",
            "cook": "our kitchen couldn't prepare your order",
            "serve": "we couldn't serve your order",
        }
        reason = state["end_reason"]
        msg = speak(f"We sincerely apologize, {reasons.get(reason, 'something went wrong')}.")
        return {"final_result": "FAILED", "status": "failed", "messages": [msg]}

    # mark reason then go to finish_fail
    def fail_order(state): return {"end_reason": "order"}
    def fail_cook(state): return {"end_reason": "cook"}
    def fail_serve(state): return {"end_reason": "serve"}

    # ---- routers (read counters/status from state) -------------------------
    def after_understand(state):
        s = state["status"]
        if s == "confirmed":
            return "cook"
        if s == "start" and state["dish_name"] and state["messages"][-1].type == "human":
            return "order_confirm"   # a fresh order was extracted
        if s == "unrelated" and state["order_retries"] <= 0:
            return "fail_order"
        return "get_input"           # reject / unrelated with attempts left

    def after_order_confirm(state):
        if state["status"] == "confirmed":
            return "cook"
        return "fail_order" if state["order_retries"] <= 0 else "get_input"

    def after_cook(state):
        if state["status"] == "ready":
            return "serve"
        return "cook" if state["cook_retries"] > 0 else "fail_cook"

    def after_serve(state):
        if state["status"] == "complete":
            return "finish_success"
        if state["serve_retries"] <= 0:
            return "fail_serve"
        if state["cook_retries"] <= 0:
            return "fail_cook"   # cook exhausted -> must not cook again
        return "cook"

    # ---- wiring ------------------------------------------------------------
    g = StateGraph(OrderState)
    for name, fn in [("greet", greet), ("get_input", get_input), ("understand", understand),
                     ("order_confirm", order_confirm), ("cook", cook), ("serve", serve),
                     ("finish_success", finish_success), ("finish_fail", finish_fail),
                     ("fail_order", fail_order), ("fail_cook", fail_cook), ("fail_serve", fail_serve)]:
        g.add_node(name, fn)

    g.add_edge(START, "greet")
    g.add_edge("greet", "get_input")
    g.add_edge("get_input", "understand")
    g.add_conditional_edges("understand", after_understand,
                            ["cook", "order_confirm", "fail_order", "get_input"])
    g.add_conditional_edges("order_confirm", after_order_confirm,
                            ["cook", "fail_order", "get_input"])
    g.add_conditional_edges("cook", after_cook, ["serve", "cook", "fail_cook"])
    g.add_conditional_edges("serve", after_serve,
                            ["finish_success", "fail_serve", "fail_cook", "cook"])
    for n in ("fail_order", "fail_cook", "fail_serve"):
        g.add_edge(n, "finish_fail")
    g.add_edge("finish_success", END)
    g.add_edge("finish_fail", END)
    return g.compile(checkpointer=checkpointer)


# --------------------------------------------------------------------------
# TEST SIMULATION
# --------------------------------------------------------------------------
def scripted(values):
    it = iter(values)
    return lambda: next(it)


def run_case(name, user_inputs, cook_script, serve_script, expected):
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    inputs = iter(user_inputs)
    app = build_graph(
        ScriptedBrain(),
        input_fn=lambda: (lambda t: (print(f"You: {t}"), t)[1])(next(inputs)),
        cook_ok=scripted(cook_script),
        serve_ok=scripted(serve_script),
    )
    final = app.invoke(initial_state(), {"recursion_limit": 100})
    ok = final["final_result"] == expected["result"] and \
        final["end_reason"] == expected.get("reason", final["end_reason"])
    print(f"-> final_result={final['final_result']} end_reason={final['end_reason'] or '-'} "
          f"| counters order/cook/serve = {final['order_retries']}/{final['cook_retries']}/{final['serve_retries']}")
    print(f"-> {name.split(':')[0]}: {'PASS' if ok else 'FAIL'} (expected {expected})")
    return ok


def run_tests():
    results = [
        run_case("TC1: unrelated, partial, reject, unavailable -> END (order retries)",
                 ["what is the capital of France?", "order 8 pizza", "no", "order 2 tacos"],
                 [], [], {"result": "FAILED", "reason": "order"}),
        run_case("TC2: cook fail, cook ok, serve fail, cook ok, serve ok -> SUCCESS",
                 ["order 2 burger"],
                 [False, True, True], [False, True], {"result": "COMPLETED"}),
        run_case("TC3: partial, reorder, cook fail/ok, serve fail, cook ok, serve fail -> FAIL",
                 ["order 8 pizza", "no", "order 2 burger"],
                 [False, True, True], [False, False], {"result": "FAILED"}),
    ]
    print(f"\n{sum(results)}/{len(results)} test cases passed")


# --------------------------------------------------------------------------
if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        app = build_graph(GroqBrain(), input_fn=lambda: input("You: "))
        final = app.invoke(initial_state(), {"recursion_limit": 100})
        print(f"\nFINAL RESULT: {final['final_result']}")