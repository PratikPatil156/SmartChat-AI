# SmartChat AI

SmartChat AI is a conversational interface built on top of LangGraph, Streamlit, and Groq. It features stateful conversation memory (via SQLite), custom CSS styling, active thread management, and real-time tool execution status indicators.

## Features

- **Custom UI:** Sleek radial background, Outfit/Inter typography, and custom sidebar layouts.
- **Avatars:** Custom user (`🧑‍💻`) and assistant (`🧠`) icons.
- **Stateful Memory:** Persists chat history across sessions using SQLite checkpointers.
- **Thread Management:** Create new threads (defaults to "Start Chat"), switch between them, and delete active threads directly from the sidebar.
- **Actionable Status:** Expandable status blocks for background tool operations (search, stock updates, calculations).
- **Custom Input Bar:** Sleek black focus borders and circular send action button.
- **LangSmith Integration:** Built-in support for LangSmith tracing and observability.

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PratikPatil156/SmartChat-AI.git
   cd SmartChat-AI
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   Create a `.env` file in the root folder:
   ```env
   GROQ_API_KEY=your_api_key_here

   # LangSmith Tracing (Optional)
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key_here
   LANGCHAIN_PROJECT=SmartChat-AI
   ```

4. **Run the app:**
   ```bash
   streamlit run frontend.py
   ```
