from datetime import datetime
from google.genai import types
from typing import Callable, Dict, Any
from .Context.SessionContext import CURRENT_SID
from . import session_store as _session_store



def bind_sid(fn: Callable[..., Any], sid: str) -> Callable[..., Any]:
    """Return a callable that injects sid as the first argument (or keyword)."""
    async def _bound(*args, **kwargs):
        return await fn(sid, *args, **kwargs)
    return _bound


async def process_agent_response(event):
    """Process and display agent response events.
    Prefer final-event text; capture latest non-empty text as fallback."""
    print(f"Event ID: {event.id}, Author: {event.author}")

    latest_text = None
    if event.content and getattr(event.content, "parts", None):
        for part in event.content.parts:
            # Only process text parts, skip any bytes/blobs
            if hasattr(part, "text") and part.text:
                txt = part.text.strip()
                if txt:
                    latest_text = txt
                    print(f"  Text: '{txt}'")

    final_response = None
    if event.is_final_response():
        if event.content and getattr(event.content, "parts", None):
            # Find the first text part
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_response = part.text.strip()
                    break
        if final_response is None:
            print("\n Final Agent Response: [No text content in final event]\n")

    # Return both: explicit final text (or None) and latest seen text for fallback
    return {"final": final_response, "latest": latest_text}


from .MainChef.context_services import GlobalContextReader

async def call_agent_async(runner, user_id, session_id, query):
    """Call the agent asynchronously with the user's query.
    Accumulate all text responses from the agent to ensure multi-step answers are captured."""

    # Inject session context (Age/Gender/Emotion/Weather) into the prompt for personalization
    # This is invisible to the user but visible to the agent
    ctx_str = ""
    try:
        sess = _session_store.user_sessions.get(session_id, {})
        age = sess.get("age_group")
        gender = sess.get("gender_guess")
        emotion = sess.get("emotion")
        
        # Get global weather context
        global_reader = GlobalContextReader()
        temp = global_reader.temperature_bucket()
        tod = global_reader.time_of_day()

        ctx_parts = []
        if age: ctx_parts.append(f"AgeGroup={age}")
        if gender: ctx_parts.append(f"Gender={gender}")
        if emotion: ctx_parts.append(f"Emotion={emotion}")
        if temp: ctx_parts.append(f"WeatherTemp={temp}")
        if tod: ctx_parts.append(f"TimeOfDay={tod}")
        
        if ctx_parts:
            ctx_str = f"[Context: {', '.join(ctx_parts)}] "
    except Exception:
        pass

    # Prepend context to the user's query
    full_text = ctx_str + query
    content = types.Content(role="user", parts=[types.Part(text=full_text)])

    token = CURRENT_SID.set(session_id)

    collected_texts = []
    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=content
        ):
            resp = await process_agent_response(event)
            
            text_chunk = None
            if isinstance(resp, dict):
                text_chunk = resp.get("latest")
            else:
                text_chunk = resp
            
            if text_chunk:
                collected_texts.append(text_chunk)
                
    except Exception as e:
        print(f"ERROR during agent run: {e}")
    finally:
        CURRENT_SID.reset(token)

    # Join all collected text parts
    final_response_text = " ".join(collected_texts).strip()

    # If final response is empty, trigger a short finalization prompt
    if not final_response_text:
        try:
            # Safe finalization anchored to original user query
            finalize_prompt = (
                "Finalize your answer to the user's request: '" + str(query) + "'. "
                "Respond with one concise, customer-facing sentence. "
                "Do not call tools; do not include internal notes."
            )
            finalize_content = types.Content(
                role="user",
                parts=[types.Part(text=finalize_prompt)],
            )
            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=finalize_content
            ):
                resp = await process_agent_response(event)
                if isinstance(resp, dict) and resp.get("final"):
                    final_response_text = resp["final"]
                elif resp:
                    final_response_text = resp
        except Exception as e:
            print(f"ERROR during finalization: {e}")

    return final_response_text or ""