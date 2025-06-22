import os
import subprocess
import time
import json

import openai
import streamlit as st

# —————————————————————————————————————————————————————————————————
# Page config must be first Streamlit command
st.set_page_config(layout="wide", page_title="Dual-LLM Playground")

# Load your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# —————————————————————————————————————————————————————————————————
# Sidebar controls
st.sidebar.title("⚙️ Settings")
# Model selection
gpt_models    = ["gpt-4o-mini", "gpt-3.5-turbo"]
local_models  = ["llama3.2"]
selected_gpt   = st.sidebar.selectbox("Cloud LLM",   gpt_models)
selected_local = st.sidebar.selectbox("Local LLM",   local_models)
# Generation parameters
temp       = st.sidebar.slider("Temperature",  0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Max Tokens",   50, 3000, 256, step=50)

# Budget configuration (cap GPT spend at €0.10)
TOTAL_BUDGET_CENTS   = 10
COST_PER_TOKEN_CENTS = 0.003
# File for persistent budget
BUDGET_FILE = "budget.json"

# Clear history & budget
def clear_all():
    st.session_state.history = []
    st.session_state.budget_used = 0.0
    try:
        os.remove(BUDGET_FILE)
    except FileNotFoundError:
        pass

if st.sidebar.button("Clear History & Budget"):
    clear_all()

# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
# Load or init budget
if "budget_used" not in st.session_state:
    try:
        with open(BUDGET_FILE, "r") as f:
            st.session_state.budget_used = float(json.load(f))
    except FileNotFoundError:
        st.session_state.budget_used = 0.0

# Sidebar metric: remaining budget
remaining = max(TOTAL_BUDGET_CENTS - st.session_state.budget_used, 0)
st.sidebar.metric("💶 Budget remaining (¢)", f"{remaining:.1f}")

# —————————————————————————————————————————————————————————————————
# App title
st.title("🌐 Dual-LLM Chat Playground")

# Display conversation history
for msg in st.session_state.history:
    role = "user" if msg["role"] == "user" else "assistant"
    st.chat_message(role).write(msg["content"])

# Chat input
user_input = st.chat_input("Type your message here...")
if user_input:
    # Save and display user message
    st.session_state.history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    col1, col2 = st.columns(2)

    # GPT response (with full history)
    with col1:
        st.subheader(f"💬 {selected_gpt}")
        if st.session_state.budget_used < TOTAL_BUDGET_CENTS:
            # Build messages for GPT
            gpt_msgs = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.history
                if m["role"] in ("user", "assistant")
            ]
            t0   = time.time()
            resp = openai.chat.completions.create(
                model=selected_gpt,
                messages=gpt_msgs,
                temperature=temp,
                max_tokens=max_tokens,
            )
            text_gpt = resp.choices[0].message.content
            st.markdown(text_gpt)
            st.caption(f"⏱ GPT took {time.time() - t0:.2f}s")

            # Update and persist budget
            tokens = resp.usage.total_tokens
            st.session_state.budget_used += tokens * COST_PER_TOKEN_CENTS
            with open(BUDGET_FILE, "w") as f:
                json.dump(st.session_state.budget_used, f)

            st.session_state.history.append({"role": "assistant", "content": text_gpt})
        else:
            st.warning("🚫 Cloud budget exhausted (10¢ spent)")
            st.session_state.history.append({
                "role": "assistant",
                "content": "[Cloud model disabled—budget exhausted]"
            })

    # Llama response (full history context)
    with col2:
        st.subheader(f"🤖 {selected_local}")
        t1 = time.time()
        history_context = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in st.session_state.history
        ) + "\nAssistant:"
        proc = subprocess.run(
            ["ollama", "run", selected_local, "-"],
            input=history_context,
            text=True,
            capture_output=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        text_llama = proc.stdout
        st.code(text_llama)
        st.caption(f"⏱ Llama took {time.time() - t1:.2f}s")
        st.session_state.history.append({"role": "assistant_local", "content": text_llama})
        st.chat_message("assistant").write(text_llama)

# —————————————————————————————————————————————————————————————————
# Footer (always visible)
st.markdown("---")
st.caption("Built with Streamlit & Ollama | Dual-LLM Chat Playground")
st.caption("Made by John Baby Nayathodan")
