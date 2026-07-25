import base64
import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Document Delta & Grounded Chat",
    page_icon="\U0001f4d0",
    layout="wide",
)

DEFAULT_API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


def _init_session() -> None:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "delta_result" not in st.session_state:
        st.session_state.delta_result = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None


_init_session()


def _secret(key: str, default: str) -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default  # no secrets.toml present (e.g. local dev) -- not an error


# --- Sidebar: backend connection ------------------------------------------------

with st.sidebar:
    st.header("Backend")
    api_base_url = st.text_input(
        "API base URL",
        value=_secret("API_BASE_URL", DEFAULT_API_BASE_URL),
        help="URL of the deployed backend API (FastAPI, e.g. on AWS App Runner).",
    ).rstrip("/")
    api_token = st.text_input(
        "API token (optional)",
        type="password",
        help="Only needed if the backend has API_AUTH_TOKEN set.",
    )

    def _headers() -> dict:
        return {"Authorization": f"Bearer {api_token}"} if api_token else {}

    try:
        health = requests.get(f"{api_base_url}/health", timeout=5)
        if health.ok:
            st.success("Backend reachable.", icon="✅")
        else:
            st.error(f"Backend returned {health.status_code}", icon="⚠️")
    except requests.RequestException as e:
        st.error(f"Cannot reach backend: {e}", icon="⚠️")

    st.divider()
    st.header("About")
    st.markdown(
        "This is a thin client — all ingestion, delta computation, and LLM "
        "inference happen on the backend API. Nothing here holds an NVIDIA "
        "API key or the document pipeline itself."
    )


# --- Document selection ---------------------------------------------------------

st.title("Document Delta Engine & Grounded Chat")

mode = st.radio(
    "Choose input", ["Use a bundled sample pair", "Upload your own PDFs"], horizontal=True
)

sample_pair_key = None
upload_a = upload_b = None

if mode == "Use a bundled sample pair":
    try:
        samples_resp = requests.get(f"{api_base_url}/samples", headers=_headers(), timeout=10)
        samples_resp.raise_for_status()
        samples = samples_resp.json()
    except requests.RequestException as e:
        samples = {}
        st.error(f"Could not fetch sample pairs from backend: {e}")

    if samples:
        options = {v["label"]: k for k, v in samples.items() if v.get("available")}
        if options:
            chosen_label = st.selectbox("Sample pair", list(options.keys()))
            sample_pair_key = options[chosen_label]
        else:
            st.warning("Backend reports no sample pairs available.")
else:
    col1, col2 = st.columns(2)
    with col1:
        upload_a = st.file_uploader("PID A (earlier revision)", type=["pdf"], key="upload_a")
    with col2:
        upload_b = st.file_uploader("PID B (later revision)", type=["pdf"], key="upload_b")

can_run = bool(sample_pair_key) or bool(upload_a and upload_b)
run_clicked = st.button("Compute Delta", type="primary", disabled=not can_run)

if run_clicked:
    with st.spinner("Calling backend: ingest -> delta -> report -> redline overlay..."):
        try:
            if sample_pair_key:
                resp = requests.post(
                    f"{api_base_url}/delta",
                    headers=_headers(),
                    data={"sample_pair": sample_pair_key},
                    timeout=120,
                )
            else:
                files = {
                    "pid_a": (upload_a.name, upload_a.getvalue(), "application/pdf"),
                    "pid_b": (upload_b.name, upload_b.getvalue(), "application/pdf"),
                }
                resp = requests.post(
                    f"{api_base_url}/delta", headers=_headers(), files=files, timeout=120
                )
            resp.raise_for_status()
            st.session_state.delta_result = resp.json()
            st.session_state.session_id = st.session_state.delta_result["session_id"]
            st.session_state.chat_history = []
        except requests.RequestException as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            st.error(f"Delta computation failed: {e} {detail}")


# --- Results ---------------------------------------------------------------

result = st.session_state.delta_result
session_id = st.session_state.session_id

if result:
    summary = result["summary"]

    st.subheader("Delta Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Added", summary.get("added", 0))
    c2.metric("Removed", summary.get("removed", 0))
    c3.metric("Modified", summary.get("modified", 0))
    c4.metric("Total Changes", summary.get("total_changes", 0))

    tab_table, tab_overlay, tab_reports, tab_trace = st.tabs(
        ["Delta Table", "Redline Overlay", "Reports", "Observability"]
    )

    with tab_table:
        rows = [
            {
                "#": idx + 1,
                "Type": item["change_type"],
                "Item Type": item["item_type"],
                "Page": item["page"],
                "Description": item["description"],
                "Old Value": item["old_value"],
                "New Value": item["new_value"],
                "Confidence": round(item["confidence"], 2),
            }
            for idx, item in enumerate(result["items"])
        ]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, height=420)
        else:
            st.info("No changes detected between the two revisions.")

    with tab_overlay:
        if result.get("has_overlay"):
            try:
                pages_resp = requests.get(
                    f"{api_base_url}/delta/{session_id}/overlay/pages",
                    headers=_headers(),
                    timeout=30,
                )
                pages_resp.raise_for_status()
                st.caption(
                    "Visual redline overlay rendered on PID B: added items in "
                    "green, removed in red, modified in orange."
                )
                for page_b64 in pages_resp.json()["pages"]:
                    st.image(base64.b64decode(page_b64), use_container_width=True)

                pdf_resp = requests.get(
                    f"{api_base_url}/delta/{session_id}/overlay.pdf",
                    headers=_headers(),
                    timeout=30,
                )
                if pdf_resp.ok:
                    st.download_button(
                        "Download annotated PDF",
                        pdf_resp.content,
                        file_name="annotated_delta.pdf",
                        mime="application/pdf",
                    )
            except requests.RequestException as e:
                st.error(f"Could not load overlay: {e}")
        else:
            st.info("No visual overlay was generated for this pair.")

    with tab_reports:
        try:
            md_resp = requests.get(
                f"{api_base_url}/delta/{session_id}/report.md", headers=_headers(), timeout=30
            )
            json_resp = requests.get(
                f"{api_base_url}/delta/{session_id}/report.json", headers=_headers(), timeout=30
            )
            if md_resp.ok:
                st.download_button(
                    "Download delta_report.md",
                    md_resp.text,
                    file_name="delta_report.md",
                    mime="text/markdown",
                )
                with st.expander("Preview Markdown report"):
                    st.markdown(md_resp.text)
            if json_resp.ok:
                st.download_button(
                    "Download delta_report.json",
                    json_resp.text,
                    file_name="delta_report.json",
                    mime="application/json",
                )
        except requests.RequestException as e:
            st.error(f"Could not load reports: {e}")

    with tab_trace:
        try:
            trace_resp = requests.get(
                f"{api_base_url}/trace/{session_id}", headers=_headers(), timeout=15
            )
            if trace_resp.ok:
                trace = trace_resp.json()
                st.caption(f"trace_id: `{trace['trace_id']}`")
                st.json(trace["root_span"], expanded=False)
                st.write("LLM calls:")
                st.json(trace["llm_calls"], expanded=False)
            else:
                st.info("No trace available yet.")
        except requests.RequestException as e:
            st.error(f"Could not load trace: {e}")

    # --- Grounded chat -------------------------------------------------------

    st.divider()
    st.subheader("Grounded Chat")

    for turn in st.session_state.chat_history:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            if turn.get("citations"):
                st.caption("Citations: " + ", ".join(turn["citations"]))

    question = st.chat_input("Ask a question about the documents or the delta...")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    history_payload = [
                        {"role": t["role"], "content": t["content"]}
                        for t in st.session_state.chat_history[:-1]
                    ]
                    chat_resp = requests.post(
                        f"{api_base_url}/chat",
                        headers=_headers(),
                        json={
                            "session_id": session_id,
                            "question": question,
                            "history": history_payload,
                        },
                        timeout=90,
                    )
                    chat_resp.raise_for_status()
                    answer = chat_resp.json()
                    st.markdown(answer["answer"])
                    citation_labels = [c["snippet"] for c in answer.get("citations", [])]
                    if citation_labels:
                        st.caption("Citations: " + ", ".join(citation_labels))
                except requests.RequestException as e:
                    answer = {"answer": f"Error calling backend: {e}"}
                    citation_labels = []
                    st.error(answer["answer"])

        st.session_state.chat_history.append(
            {"role": "assistant", "content": answer["answer"], "citations": citation_labels}
        )
else:
    st.info(
        "Pick a sample pair or upload two PID PDFs, then click **Compute Delta** "
        "to get started. Make sure the backend URL in the sidebar is reachable."
    )
