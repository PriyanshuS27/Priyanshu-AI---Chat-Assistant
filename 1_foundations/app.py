# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from dotenv import load_dotenv
import google.generativeai as genai
import json
import re
import os
import requests
from pypdf import PdfReader
from pathlib import Path
import gradio as gr
import ssl
import logging
ssl._create_default_https_context = ssl._create_unverified_context

load_dotenv(override=True)

# Basic structured logging so we can diagnose push failures and tool calls
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Diagnostic block - google.genai doesn't exist, using google.generativeai instead
# try:
#     import google.genai as _genai_diag
#     logging.info("google.genai version: %s", getattr(_genai_diag, "__version__", "unknown"))
#     logging.info(
#         "google.genai attrs: %s",
#         ",".join([a for a in dir(_genai_diag) if 'generate' in a.lower() or 'generative' in a.lower()])
#     )
# except Exception as _e:
#     logging.warning("Failed to import google.genai for diagnostics: %s", _e)

# Basic structured logging so we can diagnose push failures and tool calls
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.info("google.generativeai version: %s", getattr(genai, "__version__", "unknown"))
logging.info("genai attrs: %s", ",".join([a for a in dir(genai) if 'generate' in a.lower() or 'generative' in a.lower()]))

api_key = os.getenv("GEMINI_API_KEY")
logging.info("GEMINI_API_KEY value seen by app: %r", api_key)

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set or empty in this environment")

# Configure the google.generativeai client and use GenerativeModel.generate_content
genai.configure(api_key=api_key)

# Log notification service configuration at startup
def log_notification_config():
    """Log which notification service is configured"""
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    pushover_token = os.getenv("PUSHOVER_TOKEN")
    pushover_user = os.getenv("PUSHOVER_USER")
    
    logging.info("=== Notification Service Configuration ===")
    if tg_token and tg_chat:
        logging.info("✓ Telegram configured: bot_token=%s... chat_id=%s", tg_token[:20], tg_chat)
    else:
        logging.warning("✗ Telegram NOT configured")
    
    if pushover_token and pushover_user:
        logging.info("✓ Pushover configured (fallback)")
    else:
        logging.warning("✗ Pushover NOT configured (will be fallback)")

log_notification_config()

def get_available_models():
    """List available models from Gemini API"""
    try:
        import google.generativeai as genai_models
        models = genai_models.list_models()
        available = [m.name for m in models]
        logging.info("Available models: %s", available)
        return available
    except Exception as e:
        logging.error("Failed to list models: %s", e)
        return []

def call_gemini(prompt, model_name="gemini-2.5-flash"):
    """Call Gemini via google.generativeai.GenerativeModel.generate_content.
    Try a couple of common parameter shapes for compatibility across SDK versions.
    Returns the raw response object.
    """
    Gen = getattr(genai, "GenerativeModel", None)
    if not Gen:
        raise RuntimeError("google.generativeai.GenerativeModel not available in this environment")
    model = Gen(model_name)
    
    # Set generation config with higher token limit to avoid truncation
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,  # Increased from default to prevent truncation
    }
    
    # Try simple string argument first
    try:
        return model.generate_content(prompt, generation_config=generation_config)
    except TypeError:
        # Some versions expect a dict or list of content blocks
        try:
            return model.generate_content({"content": prompt}, generation_config=generation_config)
        except Exception:
            # last resort: try a named argument
            return model.generate_content(inputs=prompt, generation_config=generation_config)
   
def push(text):
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        try:
            logging.info("Attempting Telegram send to chat %s", tg_chat)
            url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            payload = {"chat_id": tg_chat, "text": text}
            logging.debug("Telegram URL: %s", url)
            logging.debug("Telegram payload: %s", payload)
            
            # Try with JSON first (more reliable)
            r = requests.post(url, json=payload, timeout=10, verify=False)
            
            logging.info("Telegram response status: %s", r.status_code)
            if r.status_code == 200:
                logging.info("✓ Telegram sent successfully")
                return True
            
            resp_text = r.text[:500]  # Limit response text
            logging.error("✗ Telegram API error: status=%s response=%s", r.status_code, resp_text)
            
            # Try with data format as fallback
            logging.info("Trying Telegram with data format...")
            r2 = requests.post(url, data=payload, timeout=10, verify=False)
            if r2.status_code == 200:
                logging.info("✓ Telegram sent successfully (data format)")
                return True
            
            resp_text2 = r2.text[:500]
            logging.error("✗ Telegram data format also failed: status=%s response=%s", r2.status_code, resp_text2)
            return False
            
        except requests.exceptions.Timeout as e:
            logging.error("✗ Telegram request timed out: %s", e)
            return False
        except requests.exceptions.ConnectionError as e:
            logging.error("✗ Telegram connection error (check internet): %s", e)
            return False
        except Exception as e:
            logging.exception("✗ Telegram send failed with exception: %s", e)
            return False

    # Fallback to Pushover
    token = os.getenv("PUSHOVER_TOKEN")
    user = os.getenv("PUSHOVER_USER")
    if not token or not user:
        logging.warning("✗ Neither Telegram nor Pushover configured")
        return False

    # Mask token for logs
    masked_token = token[:4] + "..." + token[-4:] if len(token) > 8 else "<masked>"
    logging.info("Attempting Pushover send (token=%s, user=%s)", masked_token, user)
    try:
        r = requests.post(
            "https://api.pushover.net/1/messages.json",
            json={
                "token": token,
                "user": user,
                "message": text,
            },
            timeout=10,
            verify=False,
        )
        try:
            body = r.text[:500]
        except Exception:
            body = "<could not read response body>"
        
        if r.status_code != 200:
            logging.error("✗ Pushover API error: status=%s response=%s", r.status_code, body)
            return False
        
        logging.info("✓ Pushover sent successfully: %s", body)
        return True
        
    except requests.exceptions.Timeout as e:
        logging.error("✗ Pushover request timed out: %s", e)
        return False
    except requests.exceptions.ConnectionError as e:
        logging.error("✗ Pushover connection error (check internet): %s", e)
        return False
    except Exception as e:
        logging.exception("✗ Pushover request failed with exception: %s", e)
        return False


def record_user_details(email, name="Name not provided", notes="not provided"):
    logging.info("record_user_details called with email=%s name=%s notes=%s", email, name, notes)
    success = push(f"Recording {name} with email {email} and notes {notes}")
    if not success:
        logging.warning("Recording saved locally but push failed for email=%s", email)
    return {"recorded": "ok", "pushover_sent": bool(success)}

def record_unknown_question(question):
    logging.info("record_unknown_question called: %s", question)
    logging.info("About to call push() for question: %s", question)
    success = push(f"Recording unknown question: {question}")
    logging.info("push() returned: %s for question: %s", success, question)
    if not success:
        logging.warning("✗ Failed to send notification for unknown question")
    else:
        logging.info("✓ Successfully notified about unknown question")
    return {"recorded": "ok", "pushover_sent": bool(success), "notification_sent": bool(success)}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


class Me:

    def __init__(self):
        self.name = "Priyanshu Sharma"
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        base_dir = Path(__file__).resolve().parent
        
        # Load resume PDF
        self.resume_path = base_dir / "me" / "Priyanshu_Sharma_Resume.pdf"
        self.resume_available = self.resume_path.is_file()
        if self.resume_available:
            logging.info("✓ Resume PDF found at: %s", self.resume_path)
        else:
            logging.warning("✗ Resume PDF not found at: %s", self.resume_path)
        
        pdf_path = base_dir / "me" / "linkedin.pdf"
        self.linkedin = ""
        if pdf_path.is_file():
            try:
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        self.linkedin += text
                # sanitize any URLs from parsed LinkedIn text to avoid leaking or hallucinated links
                if self.linkedin:
                    self.linkedin = re.sub(r'https?://\S+','', self.linkedin)
            except Exception as e:
                print(f"Warning: failed to read PDF {pdf_path}: {e}", flush=True)
        else:
            print(f"Info: {pdf_path} not found — continuing without LinkedIn text", flush=True)

        summary_path = base_dir / "me" / "summary.txt"
        if summary_path.is_file():
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    self.summary = f.read()
            except Exception as e:
                print(f"Warning: failed to read {summary_path}: {e}", flush=True)
                self.summary = "No summary available."
        else:
            print(f"Info: {summary_path} not found — using default summary", flush=True)
            self.summary = "No summary available."


    def handle_tool_call(self, tool_calls):
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)
            result = tool(**arguments) if tool else {}
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id})
        return results
   
    def system_prompt(self):
        system_prompt = f"You are acting as {self.name}. You are answering questions on {self.name}'s website, \
particularly questions related to {self.name}'s career, background, skills and experience. \
Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. \
You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. \
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "

        # Add resume availability info
        resume_info = "\n**IMPORTANT: You have a resume PDF available.**\n\
When someone asks for your resume, CV, or professional profile, respond with:\n\
'I'd be happy to share my resume with you! You can download it here: [RESUME_AVAILABLE]'\n\
Replace [RESUME_AVAILABLE] with the actual link or mention that it's available for download."
        
        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n{resume_info}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
   
    def chat(self, message, history):
        # Check if user is asking for resume
        lower_message = message.lower()
        resume_keywords = ["resume", "cv", "curriculum vitae", "my resume", "my cv", "download resume", "send resume"]
        
        if self.resume_available and any(keyword in lower_message for keyword in resume_keywords):
            logging.info("Resume request detected from user: %s", message)
            
            response_text = f"""📄 **Here's my resume!**

I've made it easy for you to download my complete resume. Just click the **📥 download button** in the chat header (top-right corner) to get my resume PDF instantly!

---

### 🎯 What's in my resume:
- **Professional Experience** - My journey as an AI & Software Engineer
- **Technical Skills** - Python, AI, Machine Learning, Full-Stack Development
- **Projects** - Real-world applications and innovative solutions
- **Education & Certifications** - Relevant qualifications and achievements

---

### 💬 After reviewing, I'm here to:
- **Discuss my experience** - Ask about specific projects or skills
- **Answer technical questions** - Deep dive into my expertise
- **Discuss opportunities** - Share your email if interested in collaborating
- **Clarify anything** - I'm happy to explain any part of my background

Feel free to ask any questions! 😊"""
            
            return response_text
        
        prompt = self.system_prompt() + "\n" + message
        # Use compatibility wrapper to call Gemini across client versions
        response = call_gemini(prompt, model_name="gemini-2.5-flash")
        
        # Check if response was truncated due to token limit
        finish_reason = getattr(response, "finish_reason", None)
        if finish_reason and "LENGTH" in str(finish_reason).upper():
            logging.warning("Response may be truncated due to token limit. Finish reason: %s", finish_reason)
        
        # Try several safe extraction methods in order
        text = None
        # 1) try direct attribute access
        try:
            text = getattr(response, "text", None)
        except Exception as e:
            print(f"Warning: direct response.text access failed: {e}", flush=True)

        # 2) if still none, try candidates
        if not text:
            try:
                if hasattr(response, "candidates") and response.candidates:
                    cand = response.candidates[0]
                    for attr in ("content", "text", "output", "parts"):
                        val = getattr(cand, attr, None)
                        if val:
                            if isinstance(val, str):
                                text = val
                                break
                            if isinstance(val, list) and len(val) > 0:
                                first = val[0]
                                if isinstance(first, str):
                                    text = first
                                else:
                                    text = getattr(first, "text", None) or str(first)
                                break
                            text = str(val)
                            break
            except Exception as e2:
                print(f"Warning: failed to extract candidate text: {e2}", flush=True)

        # 3) last-resort stringify
        if not text:
            try:
                to_dict_fn = getattr(response, "to_dict", None)
                if callable(to_dict_fn):
                    text = json.dumps(to_dict_fn(), default=str)
                else:
                    text = json.dumps(getattr(response, "__dict__", {}), default=str)
            except Exception:
                try:
                    text = str(response)
                except Exception:
                    text = "Sorry — the model returned no text."

        # At this point we have response text (or a fallback string). Process potential tool JSON.
        try:
            # extract_tool_json is defined later in the module; call at runtime
            tool_call = extract_tool_json(text)
            if tool_call:
                tool = tool_call.get("tool")
                args = tool_call.get("args", {})
                if tool in ALLOWED_TOOLS:
                    result = ALLOWED_TOOLS[tool](**args)
                    # remove the JSON snippet before showing to user
                    cleaned = re.sub(r'```json[\s\S]*?```', '', text)
                    cleaned = re.sub(r'\{\s*"tool"[\s\S]*?\}', '', cleaned)
                    return cleaned.strip()
        except Exception as e:
            print(f"Warning: tool extraction/exec failed: {e}", flush=True)

        # Clean up the response - remove any extra metadata or tool confirmations for display
        text = (text or "").strip()
        
        # Additional heuristic: if the model response looks like raw SDK/JSON
        # diagnostic output (e.g. contains 'candidates', 'model_version',
        # 'usage_metadata' etc.) or is very short/not human-readable, treat it
        # as an unanswered/out-of-scope reply and record the question.
        try:
            stripped = text
            looks_like_sdk_json = False
            if stripped.startswith("{") and any(k in stripped for k in ("\"candidates\"","\"model_version\"","\"usage_metadata\"","\"token_count\"","candidates","model_version")):
                looks_like_sdk_json = True
            # also treat extremely short or non-alphanumeric responses as non-answers
            alpha_num_chars = len(re.findall(r"[A-Za-z0-9]", stripped))
            if looks_like_sdk_json or alpha_num_chars < 20:
                logging.warning("Detected SDK-like or malformed response: looks_like_sdk=%s alpha_chars=%d", looks_like_sdk_json, alpha_num_chars)
                try:
                    logging.info("Recording unknown question via SDK detection: %s", message)
                    record_unknown_question(message)
                    text = "I'm sorry — I couldn't answer that. I've recorded the question for follow-up."
                    return text
                except Exception as e:
                    logging.exception("Automatic record for SDK-like response failed: %s", e)
                    print(f"Warning: automatic record for SDK-like response failed: {e}", flush=True)
        except Exception as _e:
            logging.exception("SDK-like response detection failed: %s", _e)
            print(f"Warning: SDK-like response detection failed: {_e}", flush=True)

        # Heuristic fallback: if the model replied in plain language that it will
        # record or make a note (e.g. "I'll record that", "I will make a note"),
        # treat that as an implicit record request and call `record_unknown_question`
        # with the original user message. This is a safety net for models that
        # describe the action instead of emitting the JSON tool call.
        try:
            lower_text = text.lower()
            fallback_phrases = [
                # Recording phrases
                "i will record",
                "i'll record",
                "i've recorded",
                "i have recorded",
                "i can record",
                "i could record",
                "i will make a note",
                "i'll make a note",
                "i have made a note",
                "i'll note",
                "i will note",
                "i've noted",
                "i have noted",
                "i will record that",
                "recorded your question",
                "i've recorded your",
                "record that",
                "record that question",
                "i can help record",
                "i'll help record",
                # Out-of-scope phrases (when model politely declines)
                "outside the scope",
                "outside my scope",
                "outside of my scope",
                "not related to my professional",
                "not related to my background",
                "not my area of expertise",
                "outside of my expertise",
                "that question is outside",
                "that's outside the scope",
                "i'm afraid that's",
                "i'm sorry, that question is outside",
                "outside of my knowledge",
                "not something i can",
                "not something i'm able to",
            ]
            if any(p in lower_text for p in fallback_phrases):
                logging.info("Detected fallback phrase in response, calling record_unknown_question for: %s", message)
                try:
                    result = record_unknown_question(message)
                    logging.info("Fallback record result: %s", result)
                except Exception as e:
                    logging.exception("Fallback record failed: %s", e)
                    print(f"Warning: fallback record failed: {e}", flush=True)
        except Exception as e:
            logging.exception("Fallback detection failed: %s", e)
            print(f"Warning: fallback detection failed: {e}", flush=True)

        return text
   

ALLOWED_TOOLS = {
  "record_user_details": record_user_details,
  "record_unknown_question": record_unknown_question,
}

def extract_tool_json(text):
    # naive: find first {...} JSON block that contains "tool"
    m = re.search(r'(\{\s*"tool"[\s\S]*?\})', text)
    if not m:
        # also try code-fence JSON
        m = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


# ========== SETUP FASTAPI ==========
me = Me()

app = FastAPI(title="Priyanshu AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend HTML)
frontend_path = Path(__file__).resolve().parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")

class ChatRequest(BaseModel):
    message: str
    history: list = []

class ChatResponse(BaseModel):
    reply: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = me.chat(req.message, req.history)
    return {"reply": reply}

@app.get("/resume")
def resume_info():
    if me.resume_available:
        return {
            "available": True,
            "path": str(me.resume_path)
        }
    return {"available": False}

@app.get("/")
def serve_frontend():
    """Serve the frontend HTML"""
    frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(str(frontend_path), media_type="text/html")
    return {"error": "Frontend not found"}


if __name__ == "__main__":
    RUN_GRADIO = os.getenv("RUN_GRADIO", "false").lower() == "true"
    
    if RUN_GRADIO:
        # Launch Gradio UI
        port = int(os.getenv("PORT", 7860))
        
        try:
            # Create custom Gradio interface with file download capability
            with gr.Blocks(title="Priyanshu Sharma - AI Bot") as demo:
                gr.Markdown("# 👋 Welcome to Priyanshu's Portfolio Assistant")
                gr.Markdown("Ask me anything about Priyanshu's background, skills, and experience!")
                
                # Define suggestion prompts
                suggestion_prompts = [
                    "💼 Tell me about yourself",
                    "🎯 What are your key skills?",
                    "📄 Send me your resume",
                    "💬 How can I contact you?",
                    "🚀 What projects have you built?",
                    "🔗 Where can I find your LinkedIn?"
                ]
                
                # Create a custom chat interface with suggestions
                with gr.Column():
                    # Suggestion buttons above the input
                    gr.Markdown("### Quick suggestions:")
                    with gr.Row():
                        suggestion_buttons = [
                            gr.Button(prompt, size="sm") 
                            for prompt in suggestion_prompts
                        ]
                    
                    # Main chat interface
                    chat_interface = gr.ChatInterface(me.chat)
                    
                    # Connect suggestion buttons to the textbox input
                    # Get the textbox component from chat_interface
                    if hasattr(chat_interface, 'textbox'):
                        textbox = chat_interface.textbox
                    elif hasattr(chat_interface, 'input_textbox'):
                        textbox = chat_interface.input_textbox
                    else:
                        # Fallback: find first textbox in chat_interface
                        textbox = None
                        for component in chat_interface.components:
                            if isinstance(component, gr.Textbox):
                                textbox = component
                                break
                    
                    # If we found the textbox, connect buttons to it
                    if textbox is not None:
                        for btn, prompt in zip(suggestion_buttons, suggestion_prompts):
                            btn.click(
                                fn=lambda p=prompt: p,
                                outputs=textbox,
                                queue=False
                            )
                
                # Resume file display (always available for download)
                if me.resume_available:
                    gr.Markdown("---")
                    gr.Markdown("### 📄 Resume Available")
                    gr.File(
                        value=str(me.resume_path),
                        label="Download Resume",
                        interactive=False,
                        type="filepath"
                    )
            
            demo.launch(server_name="0.0.0.0", server_port=port, share=False)
            
        except TypeError:
            # Fallback for older Gradio versions
            try:
                iface = gr.ChatInterface(me.chat)
                iface.launch(server_name="0.0.0.0", server_port=port)
            except Exception:
                # Last resort: plain launch
                gr.ChatInterface(me.chat).launch()
    else:
        # Launch FastAPI (default)
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)

