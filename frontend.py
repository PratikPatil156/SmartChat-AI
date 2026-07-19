import streamlit as st
from backend import chatbot, retrieve_all_threads, llm
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid
import sqlite3

# Custom CSS to style active delete button cleanly
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Inter:wght@400;500;600&display=swap');

    /* Styling for the circular, neat delete buttons in sidebar column 2 */
    div[data-testid="column"]:last-child button {
        background-color: transparent !important;
        color: #888888 !important;
        border: none !important;
        padding: 0 !important;
        font-size: 1.1rem !important;
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        line-height: 32px !important;
        border-radius: 50% !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin-top: 4px !important;
        box-shadow: none !important;
    }
    div[data-testid="column"]:last-child button:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border: none !important;
    }
    div[data-testid="column"]:last-child button:active {
        background-color: rgba(255, 255, 255, 0.15) !important;
        border: none !important;
    }
    
    /* Left align all sidebar buttons */
    [data-testid="stSidebar"] button {
        text-align: left !important;
    }

    /* Style the outer chat input container (make it seamless) */
    div[data-testid="stChatInput"] {
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Style the inner wrapper div of stChatInput directly */
    div[data-testid="stChatInput"] > div {
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        border-radius: 12px !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
    }
    
    /* Focus outline color on inner wrapper: clean, modern black */
    div[data-testid="stChatInput"] > div:focus-within {
        border-color: #000000 !important;
        box-shadow: 0 0 0 1px #000000 !important;
    }

    /* Completely eliminate any internal red focus outlines/borders/shadows from Streamlit's elements */
    div[data-testid="stChatInput"] textarea {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stChatInput"] textarea:focus {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Style the send button container to be a premium black circle with a white arrow */
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-radius: 50% !important;
        border: none !important;
        width: 32px !important;
        height: 32px !important;
        min-height: 32px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        transition: background-color 0.2s ease, transform 0.1s ease !important;
    }

    /* Style the arrow/icon to be white */
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"] svg {
        color: #ffffff !important;
        fill: currentColor !important;
    }

    /* Hover effect: slightly lighter black */
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:hover:not(:disabled) {
        background-color: #222222 !important;
    }

    /* Click scale effect */
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:active:not(:disabled) {
        transform: scale(0.95) !important;
    }

    /* Style the disabled state of the send button */
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:disabled {
        background-color: #f0f0f0 !important;
        color: #cccccc !important;
        cursor: not-allowed !important;
    }
    div[data-testid="stChatInput"] button[data-testid="stChatInputSubmitButton"]:disabled svg {
        color: #cccccc !important;
        fill: currentColor !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================== Utilities ===========================
def generate_thread_id():
    return uuid.uuid4()

def reset_chat():
    thread_id = generate_thread_id()
    st.session_state["thread_id"] = thread_id
    add_thread(thread_id)
    # Load empty history
    st.session_state["message_history"] = []

def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

def load_conversation(thread_id):
    state = chatbot.get_state(config={"configurable": {"thread_id": thread_id}})
    # Check if messages key exists in state values, return empty list if not
    return state.values.get("messages", [])

# SQLite database functions for thread titles
def get_db_connection():
    return sqlite3.connect("chatbot.db", check_same_thread=False)

def init_title_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS thread_titles (
            thread_id TEXT PRIMARY KEY,
            title TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_thread_title(thread_id, title):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO thread_titles (thread_id, title)
        VALUES (?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET title=excluded.title
    """, (str(thread_id), title))
    conn.commit()
    conn.close()

def get_saved_thread_title(thread_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT title FROM thread_titles WHERE thread_id=?", (str(thread_id),))
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None
    finally:
        conn.close()

def delete_thread_from_db(thread_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM checkpoints WHERE thread_id=?", (str(thread_id),))
        cursor.execute("DELETE FROM writes WHERE thread_id=?", (str(thread_id),))
        cursor.execute("DELETE FROM thread_titles WHERE thread_id=?", (str(thread_id),))
        conn.commit()
    except Exception as e:
        print(f"Error deleting thread {thread_id}: {e}")
    finally:
        conn.close()

# Generate topic title using Groq LLM
def generate_title_from_llm(messages):
    if not messages:
        return "Empty Chat"
    
    # Format last few messages to give context to the LLM
    chat_summary_context = ""
    for msg in messages[-6:]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        chat_summary_context += f"{role}: {msg.content}\n"
        
    prompt = f"""You are a chat title generator. Summarize the following conversation segment into a single, extremely brief, highly specific topic-based title of 3-5 words. Do not use quotes, punctuation, or explanations. Just output the clean title.

Conversation:
{chat_summary_context}

Title:"""
    try:
        response = llm.invoke(prompt)
        title = response.content.strip()
        # Clean quotes and punctuation
        title = title.replace('"', '').replace("'", "").replace(".", "").strip()
        if len(title) > 28:
            title = title[:25] + "..."
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        return None

def get_thread_title(thread_id):
    # Try to fetch saved title from DB
    saved_title = get_saved_thread_title(thread_id)
    if saved_title:
        return saved_title
    
    # Fallback to first human message as a quick name if not generated yet
    try:
        messages = load_conversation(thread_id)
        if messages:
            for msg in messages:
                if isinstance(msg, HumanMessage) and msg.content:
                    text = msg.content.strip()
                    if len(text) > 28:
                        return text[:25] + "..."
                    return text
    except Exception:
        pass
    return "Start Chat"

# Initialize DB on startup
init_title_db()

# ======================= Session Initialization ===================
if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieve_all_threads()

add_thread(st.session_state["thread_id"])

if "message_history" not in st.session_state:
    # Load history of the active thread from database on startup
    messages = load_conversation(st.session_state["thread_id"])
    temp_messages = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        temp_messages.append({"role": role, "content": msg.content})
    st.session_state["message_history"] = temp_messages

st.sidebar.markdown(
    """
    <div style="padding: 10px 0px; margin-bottom: 15px; border-bottom: 1px solid rgba(0,0,0,0.1);">
        <h2 style="font-family: 'Outfit', sans-serif; font-size: 1.5rem; font-weight: 800; color: #000000; display: flex; align-items: center; gap: 10px; margin: 0; letter-spacing: -0.02em;">
            <span style="background: linear-gradient(135deg, #a78bfa 0%, #6d28d9 100%); padding: 6px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; font-size: 1.15rem;">🧠</span>
            SmartChat AI
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# Simple, full-width New Chat button
if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()

st.sidebar.header("My Conversations")

# Render conversations list
for thread_id in st.session_state["chat_threads"][::-1]:
    title = get_thread_title(thread_id)
    is_active = (thread_id == st.session_state["thread_id"])
    
    if is_active:
        # Show select button and delete button next to each other ONLY for the active chat!
        col1, col2 = st.sidebar.columns([0.84, 0.16])
        with col1:
            st.button(f"💬 {title}", key=f"btn_{thread_id}", use_container_width=True)
        with col2:
            if st.button("🗑️", key=f"del_{thread_id}", use_container_width=True):
                delete_thread_from_db(thread_id)
                if thread_id in st.session_state["chat_threads"]:
                    st.session_state["chat_threads"].remove(thread_id)
                
                # Switch thread
                if st.session_state["chat_threads"]:
                    st.session_state["thread_id"] = st.session_state["chat_threads"][-1]
                else:
                    st.session_state["thread_id"] = generate_thread_id()
                    add_thread(st.session_state["thread_id"])
                
                # Reload active history
                messages = load_conversation(st.session_state["thread_id"])
                temp_messages = []
                for msg in messages:
                    role = "user" if isinstance(msg, HumanMessage) else "assistant"
                    temp_messages.append({"role": role, "content": msg.content})
                st.session_state["message_history"] = temp_messages
                st.rerun()
    else:
        # Inactive chats are rendered as a clean, simple, full-width button
        if st.sidebar.button(title, key=f"btn_{thread_id}", use_container_width=True):
            st.session_state["thread_id"] = thread_id
            messages = load_conversation(thread_id)
            temp_messages = []
            for msg in messages:
                role = "user" if isinstance(msg, HumanMessage) else "assistant"
                temp_messages.append({"role": role, "content": msg.content})
            st.session_state["message_history"] = temp_messages
            st.rerun()

# ============================ Main UI ============================

# Custom avatars for chat bubbles
AVATARS = {
    "user": "🧑‍💻",
    "assistant": "🧠"
}

# Render history
for message in st.session_state["message_history"]:
    with st.chat_message(message["role"], avatar=AVATARS.get(message["role"])):
        st.text(message["content"])

user_input = st.chat_input("Type here")

if user_input:
    # Show user's message
    st.session_state["message_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.text(user_input)

    CONFIG = {
        "configurable": {"thread_id": st.session_state["thread_id"]},
        "metadata": {"thread_id": st.session_state["thread_id"]},
        "run_name": "chat_turn",
    }

    # Assistant streaming block
    with st.chat_message("assistant", avatar="🧠"):
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):
                # 1. Start indicator: When LLM outputs a tool call request
                if isinstance(message_chunk, AIMessage) and getattr(message_chunk, "tool_calls", None):
                    for tc in message_chunk.tool_calls:
                        t_name = tc["name"]
                        if t_name == "DuckDuckGoSearchRun":
                            lbl = "🔍 Searching the web..."
                        elif t_name == "get_stock_price":
                            lbl = "📊 Fetching stock price data..."
                        elif t_name == "calculator":
                            lbl = "🧮 Performing calculation..."
                        else:
                            lbl = f"🔧 Running {t_name}..."
                            
                        status_holder["box"] = st.status(lbl, state="running", expanded=True)

                # 2. End indicator: When the tool finishes and returns its message
                if isinstance(message_chunk, ToolMessage):
                    t_name = getattr(message_chunk, "name", "tool")
                    if t_name == "DuckDuckGoSearchRun":
                        fin_lbl = "🔍 Web Search Completed"
                    elif t_name == "get_stock_price":
                        fin_lbl = "📈 Stock Data Retrieved"
                    elif t_name == "calculator":
                        fin_lbl = "🧮 Calculation Completed"
                    else:
                        fin_lbl = f"✅ {t_name} Finished"
                        
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(fin_lbl, state="complete", expanded=False)
                    else:
                        status_holder["box"].update(label=fin_lbl, state="complete", expanded=False)
                        
                    with status_holder["box"]:
                        st.write(message_chunk.content)

                if isinstance(message_chunk, AIMessage):
                    yield message_chunk.content

        ai_message = st.write_stream(ai_only_stream())

        if status_holder["box"] is not None:
            status_holder["box"].update(state="complete", expanded=False)

    # Save assistant message
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )

    # Trigger title generation in the background/right after AI reply
    messages = load_conversation(st.session_state["thread_id"])
    new_title = generate_title_from_llm(messages)
    if new_title:
        save_thread_title(st.session_state["thread_id"], new_title)
        st.rerun()