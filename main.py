import os
import subprocess
import time

import openai
import streamlit as st

# —————————————————————————————————————————————————————————————————
# Load your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# —————————————————————————————————————————————————————————————————
# Sidebar settings
gpt_models = ["gpt-4o-mini", "gpt-3.5-turbo"]
local_models = ["llama3.2"]
selected_gpt = st.sidebar.selectbox("Cloud LLM", gpt_models)
selected_local = st.sidebar.selectbox("Local LLM", local_models)
temp = st.sidebar.slider("Temperature", 0.0, 1.0, 0.7)
max_tokens = st.sidebar.slider("Max Tokens", 50, 3000, 256, step=50)
if st.sidebar.button("Clear History"):
    st.session_state.history = []

# —————————————————————————————————————————————————————————————————
# Main app layout
st.set_page_config(layout="wide")
st.title("🌐 Dual-LLM Chat Playground")

# Initialize conversation history
if "history" not in st.session_state:
    st.session_state.history = []

# Display existing messages
for msg in st.session_state.history:
    role = "user" if msg["role"] == "user" else "assistant"
    st.chat_message(role).write(msg["content"])

# Chat input (unlimited)
user_input = st.chat_input("Type your message here...")
if user_input:
    # Save and show user message
    st.session_state.history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Prepare full context for both models
    history_context = "\n".join(
        f"{('User' if m['role']=='user' else 'Assistant')}: {m['content']}"
        for m in st.session_state.history
    ) + "\nAssistant:"

    col1, col2 = st.columns(2)

    # GPT response (streaming)
    with col1:
        st.subheader(f"💬 {selected_gpt}")
        placeholder = st.empty()
        t0 = time.time()
        text_gpt = ""
        for chunk in openai.chat.completions.create(
            model=selected_gpt,
            messages=[{"role": "user", "content": history_context}],
            stream=True,
            temperature=temp,
            max_tokens=max_tokens,
        ):
            delta = getattr(chunk.choices[0].delta, "content", None)
            if delta:
                text_gpt += delta
                placeholder.markdown(text_gpt + "▌")
        placeholder.markdown(text_gpt)
        st.caption(f"⏱ {time.time() - t0:.2f}s")
        # Save and display in history
        st.session_state.history.append({"role": "assistant", "content": text_gpt})
        st.chat_message("assistant").write(text_gpt)

    # Local Llama response (with full history context)
    with col2:
        st.subheader(f"🤖 {selected_local}")
        t1 = time.time()
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
        st.caption(f"⏱ {time.time() - t1:.2f}s")
        # Save and display
        st.session_state.history.append({"role": "assistant_local", "content": text_llama})
        st.chat_message("assistant").write(text_llama)

# —————————————————————————————————————————————————————————————————
# Footer
st.markdown("---")
st.caption("Built with Streamlit & Ollama | Dual-LLM Chat Playground")
st.caption("Made by John Baby Nayathodan")
