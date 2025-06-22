import os import subprocess import time import json import shutil

import openai import streamlit as st


Page config

st.set_page_config(layout="wide", page_title="Dual-LLM Chat Playground")

Load OpenAI key from env or secrets

oai_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY") openai.api_key = oai_key

Admin password from secrets

ADMIN_PW = st.secrets.get("ADMIN_PW")

Sidebar settings

st.sidebar.title("⚙️ Settings")

Admin unlock panel

if "admin_unlocked" not in st.session_state: st.session_state.admin_unlocked = False admin_input = st.sidebar.text_input("🔒 Admin password", type="password", key="admin_input") if st.sidebar.button("🔓 Unlock", key="unlock_btn"): if ADMIN_PW and admin_input == ADMIN_PW: st.session_state.admin_unlocked = True st.sidebar.success("🔓 Admin unlocked") else: st.sidebar.error("❌ Wrong password")

Clear history & budget (admin only)

def clear_all(): st.session_state.history = [] st.session_state.budget_used = 0.0 try: os.remove("budget.json") except FileNotFoundError: pass

if st.session_state.admin_unlocked: if st.sidebar.button("🚨 Clear History & Budget", key="clear_btn"): clear_all() st.sidebar.info("🔄 History & budget reset") st.experimental_rerun() else: st.sidebar.write("Enter password and click Unlock to reset.")

Model selection & parameters

gpt_models    = ["gpt-4o-mini", "gpt-3.5-turbo"] local_models  = ["llama3.2"] selected_gpt   = st.sidebar.selectbox("Cloud LLM",   gpt_models) selected_local = st.sidebar.selectbox("Local LLM",   local_models) temp           = st.sidebar.slider("Temperature",    0.0, 1.0, 0.7) max_tokens     = st.sidebar.slider("Max Tokens",     50, 3000, 256, step=50)

Toggle for local LLM

enable_local = st.sidebar.checkbox("Enable local LLM", value=True)

# Budget configuration (€0.10 cap)

TOTAL_BUDGET_CENTS   = 10 COST_PER_TOKEN_CENTS = 0.003 BUDGET_FILE          = "budget.json"

Initialize session state & load persisted budget

if "history" not in st.session_state: st.session_state.history = [] if "budget_used" not in st.session_state: try: with open(BUDGET_FILE, "r") as f: st.session_state.budget_used = float(json.load(f)) except FileNotFoundError: st.session_state.budget_used = 0.0

Sidebar metric: remaining budget

remaining = max(TOTAL_BUDGET_CENTS - st.session_state.budget_used, 0) st.sidebar.metric("💶 Budget remaining (¢)", f"{remaining:.1f}")

Main title

st.title("🌐 Dual-LLM Chat Playground")

Display chat history

for msg in st.session_state.history: role = "user" if msg["role"] == "user" else "assistant" st.chat_message(role).write(msg["content"])

Chat input

user_input = st.chat_input("Type your message here…")

Only proceed if input provided

if user_input: st.session_state.history.append({"role": "user", "content": user_input}) st.chat_message("user").write(user_input)

col1, col2 = st.columns(2)

# — GPT-4o-mini response\    with col1:
    st.subheader(f"💬 {selected_gpt}")
    if st.session_state.budget_used < TOTAL_BUDGET_CENTS:
        gpt_msgs = [{"role": m["role"], "content": m["content"]}
                    for m in st.session_state.history if m["role"] in ("user","assistant")]
        t0 = time.time()
        resp = openai.chat.completions.create(
            model=selected_gpt,
            messages=gpt_msgs,
            temperature=temp,
            max_tokens=max_tokens,
        )
        text_gpt = resp.choices[0].message.content
        st.markdown(text_gpt)
        st.caption(f"⏱ GPT took {time.time() - t0:.2f}s")

        tokens = resp.usage.total_tokens
        st.session_state.budget_used += tokens * COST_PER_TOKEN_CENTS
        with open(BUDGET_FILE, "w") as f:
            json.dump(st.session_state.budget_used, f)

        st.session_state.history.append({"role": "assistant", "content": text_gpt})
    else:
        st.warning("🚫 Cloud budget exhausted (10¢ spent)")
        st.session_state.history.append({"role":"assistant","content":"[Budget exhausted—cloud disabled]"})

# — llama3.2 response
with col2:
    st.subheader(f"🤖 {selected_local}")
    if enable_local and shutil.which("ollama"):
        try:
            t1 = time.time()
            history_ctx = "\n".join(f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}" for m in st.session_state.history) + "\nAssistant:"
            proc = subprocess.run(
                ["ollama","run",selected_local,"-"],
                input=history_ctx, text=True, capture_output=True, check=True,
                encoding="utf-8", errors="replace"
            )
            text_llama = proc.stdout
            st.code(text_llama)
            st.caption(f"⏱ Llama took {time.time() - t1:.2f}s")
            st.session_state.history.append({"role":"assistant_local","content":text_llama})
            st.chat_message("assistant").write(text_llama)
        except Exception as e:
            st.error(f"Local model error: {e}")
    else:
        st.info("Local LLM disabled or unavailable.")

— Footer — always visible

st.markdown("---") st.caption("Built with Streamlit & Ollama | Dual-LLM Chat Playground") st.caption("Made by John Baby Nayathodan")

