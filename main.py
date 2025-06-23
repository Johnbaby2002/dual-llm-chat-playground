import os
import subprocess
import time
import json
import shutil

import openai
import streamlit as st
from streamlit.errors import StreamlitAPIException

# Page configuration
st.set_page_config(layout="wide", page_title="Dual-LLM Chat Playground")

# Load OpenAI API key
oai_key = os.getenv("OPENAI_API_KEY")
if not oai_key:
    try:
        oai_key = st.secrets["OPENAI_API_KEY"]
    except (StreamlitAPIException, KeyError):
        oai_key = None
if not oai_key:
    st.error("No OPENAI_API_KEY found. Set it as an env var or in .streamlit/secrets.toml.")
    st.stop()
openai.api_key = oai_key

# Load admin password (env or secrets)
ADMIN_PW = os.getenv("ADMIN_PW")
if not ADMIN_PW:
    try:
        ADMIN_PW = st.secrets["ADMIN_PW"]
    except (StreamlitAPIException, KeyError):
        ADMIN_PW = None

# Sidebar settings
st.sidebar.title("Settings")

# Admin unlock panel
def unlock_admin():
    if ADMIN_PW and st.session_state.get("admin_input") == ADMIN_PW:
        st.session_state.admin_unlocked = True
        st.sidebar.success("Admin unlocked")
    else:
        st.sidebar.error("Wrong password")

if "admin_unlocked" not in st.session_state:
    st.session_state.admin_unlocked = False

st.sidebar.text_input("Admin password", type="password", key="admin_input")
st.sidebar.button("Unlock admin", on_click=unlock_admin)

# Admin-only clear history & budget
def clear_all():
    # Reset in-memory state
    st.session_state.history = []
    st.session_state.budget_used = 0.0
    # Remove persisted budget file
    try:
        os.remove("budget.json")
    except FileNotFoundError:
        pass
    # Attempt to rerun for fresh UI; ignore if unavailable
    try:
        st.experimental_rerun()
    except AttributeError:
        pass

if st.session_state.admin_unlocked:
    st.sidebar.button("Clear History & Budget", on_click=clear_all)
else:
    st.sidebar.write("Enter password and click Unlock to reset.")

# Model selection & parameters
gpt_models = ["gpt-4o-mini", "gpt-3.5-turbo"]
local_models = ["llama3.2"]
selected_gpt = st.sidebar.selectbox("Cloud LLM", gpt_models)
selected_local = st.sidebar.selectbox("Local LLM", local_models)
temp = st.sidebar.slider("Temperature", 0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Max Tokens", 50, 3000, 256, step=50)

# Local LLM toggle
enable_local = st.sidebar.checkbox("Enable local LLM", value=True)

# Budget configuration (capped at €0.10)
TOTAL_BUDGET_CENTS = 10  # cents
COST_PER_TOKEN_CENTS = 0.003  # cost per token in cents
BUDGET_FILE = "budget.json"

# Initialize session state and load budget
if "history" not in st.session_state:
    st.session_state.history = []
if "budget_used" not in st.session_state:
    try:
        with open(BUDGET_FILE, "r") as f:
            st.session_state.budget_used = float(json.load(f))
    except FileNotFoundError:
        st.session_state.budget_used = 0.0

# Sidebar: show remaining budget
remaining = max(TOTAL_BUDGET_CENTS - st.session_state.budget_used, 0)
st.sidebar.metric("Budget remaining (¢)", f"{remaining:.1f}")

# App title
st.title("Dual-LLM Chat Playground")

# Display conversation history
for msg in st.session_state.history:
    role = "user" if msg["role"] == "user" else "assistant"
    st.chat_message(role).write(msg["content"])

# Chat input
user_input = st.chat_input("Type your message here...")

if user_input:
    # Record and show user message
    st.session_state.history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    col1, col2 = st.columns(2)

    # GPT response
    with col1:
        st.subheader(f"GPT: {selected_gpt}")
        if st.session_state.budget_used < TOTAL_BUDGET_CENTS:
            messages = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.history
                if m["role"] in ("user", "assistant")
            ]
            t0 = time.time()
            resp = openai.chat.completions.create(
                model=selected_gpt,
                messages=messages,
                temperature=temp,
                max_tokens=max_tokens,
            )
            text_gpt = resp.choices[0].message.content
            st.markdown(text_gpt)
            st.caption(f"Time: {time.time() - t0:.2f}s")
            tokens = resp.usage.total_tokens
            st.session_state.budget_used += tokens * COST_PER_TOKEN_CENTS
            with open(BUDGET_FILE, "w") as f:
                json.dump(st.session_state.budget_used, f)
            st.session_state.history.append({"role": "assistant", "content": text_gpt})
        else:
            st.warning("Cloud budget exhausted")

    # Local LLM response
    with col2:
        st.subheader(f"Local: {selected_local}")
        if enable_local and shutil.which("ollama"):
            try:
                ctx = "\n".join(
                    f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in st.session_state.history
                ) + "\nAssistant:"
                t1 = time.time()
                proc = subprocess.run(
                    ["ollama", "run", selected_local, "-"],
                    input=ctx,
                    text=True,
                    capture_output=True,
                    check=True,
                    encoding="utf-8",
                    errors="replace",
                )
                text_loc = proc.stdout
                st.code(text_loc)
                st.caption(f"Time: {time.time() - t1:.2f}s")
                st.session_state.history.append({"role": "assistant_local", "content": text_loc})
                st.chat_message("assistant").write(text_loc)
            except Exception as e:
                st.error(f"Local LLM error: {e}")
        else:
            st.info("Local LLM disabled or unavailable.")

# Footer
st.markdown("---")
st.caption("Built with Streamlit & Ollama | Dual-LLM Chat Playground")
st.caption("Made by John Baby Nayathodan")
