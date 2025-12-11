import os
import io
import json
import datetime as dt
from typing import List, Dict, Any, Optional

import streamlit as st

from backend.job_sources import search_jobs_with_perplexity
from backend.resume_tailor import generate_tailored_resume_and_email
from backend.apply_bot import build_application_payload

st.set_page_config(
    page_title="AutoApply AI",
    page_icon="💼",
    layout="wide",
)


# ------------ Helper state ---------------

def init_state():
    defaults = {
        "jobs": [],
        "applications": [],
        "profile": {},
        "last_scan": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

# ------------ Sidebar --------------------

with st.sidebar:
    st.markdown("## ⚙️ Settings")

    st.markdown("### 🔑 API keys")
    openai_key = st.text_input(
        "OpenAI API key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
    )
    perplexity_key = st.text_input(
        "Perplexity API key",
        type="password",
        value=os.getenv("PERPLEXITY_API_KEY", ""),
    )

    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key
    if perplexity_key:
        os.environ["PERPLEXITY_API_KEY"] = perplexity_key

    st.markdown("### 🎯 Job preferences")
    target_titles = st.text_input(
        "Target titles (comma separated)",
        "Software Engineer, AI Engineer, Machine Learning Engineer",
    )
    locations = st.text_input(
        "Preferred locations (comma separated)",
        "United States, Remote",
    )
    must_have_keywords = st.text_input("Must-have keywords", "Python, SQL, Machine Learning")
    nice_to_have_keywords = st.text_input(
        "Nice-to-have keywords",
        "LLMs, GenAI, OpenAI, RAG",
    )

    # age in DAYS, up to 3 weeks
    max_job_age_days = st.slider(
        "Max job age (days)",
        min_value=1,
        max_value=21,   # 3 weeks
        value=14,       # default 2 weeks
        step=1,
    )

    # allow more jobs per scan
    max_jobs = st.slider(
        "Max jobs per scan",
        min_value=20,
        max_value=200,
        value=100,
        step=20,
    )

    st.markdown("### 📄 Resume / Profile")
    uploaded_cv = st.file_uploader(
        "Upload base resume (PDF or TXT)",
        type=["pdf", "txt"],
    )
    profile_summary = st.text_area(
        "Short profile summary",
        "AI graduate on OPT looking for full-time roles in AI / ML / Data.",
        height=80,
    )

    auto_apply_toggle = st.checkbox(
        "Automatically prepare applications for all new jobs",
        value=True,
    )

    if st.button("💾 Save profile"):
        st.session_state["profile"] = {
            "target_titles": target_titles,
            "locations": locations,
            "must_have_keywords": must_have_keywords,
            "nice_to_have_keywords": nice_to_have_keywords,
            "profile_summary": profile_summary,
        }
        st.success("Profile saved in session.")

# ------------ Main UI --------------------

st.title("💼 AutoApply AI – Job Search Copilot")
st.caption("Fetch fresh jobs, tailor resume & email with AI. You keep final control on where to submit.")

tab_feed, tab_queue, tab_profile = st.tabs(
    ["📡 Job Feed", "📨 Application Queue", "👤 Profile & Logs"]
)

# ----- PROFILE & LOGS TAB -----

with tab_profile:
    st.subheader("Current profile")
    st.json(st.session_state.get("profile", {}))

    st.subheader("System notes")
    st.markdown(
        """
        - Jobs are fetched using the Perplexity API and web search.
        - LinkedIn / Dice links are de-prioritized by the prompt, but may still appear.
        - Actual final submission to company portals is **NOT** automated in this demo – instead, the app prepares a tailored resume + email payload for you.
        - You can integrate the `backend/apply_bot.py` module with custom scripts (e.g., email sender, ATS API, or browser automation) if you want full automation.
        """
    )

    st.subheader("Last scan")
    last_scan = st.session_state.get("last_scan")
    if last_scan:
        st.write(f"Last scan at: {last_scan}")
    else:
        st.write("No scans yet.")

# ----- JOB FEED TAB -----

with tab_feed:
    st.markdown("### 🔍 Scan for fresh jobs")

    col1, col2 = st.columns([1, 1])
    with col1:
        query_extra = st.text_input(
            "Extra query (e.g. internship, specific company)",
            "",
            help="This will be added to the search prompt.",
        )
    with col2:
        st.write("")
        st.write("Jobs will be sorted by **freshness** (newest first).")

    scan_clicked = st.button("🚀 Scan now")

    if scan_clicked:
        if not os.getenv("PERPLEXITY_API_KEY"):
            st.error("Please provide a Perplexity API key in the sidebar.")
        else:
            with st.spinner("Contacting Perplexity & searching the web for jobs..."):
                try:
                    jobs = search_jobs_with_perplexity(
                        target_titles=st.session_state["profile"].get("target_titles", ""),
                        locations=st.session_state["profile"].get("locations", ""),
                        must_have_keywords=st.session_state["profile"].get("must_have_keywords", ""),
                        nice_to_have_keywords=st.session_state["profile"].get("nice_to_have_keywords", ""),
                        max_age_hours=max_job_age_days * 24,  # days → hours
                        max_results=max_jobs,
                        extra_query=query_extra,
                    )

                    # Sort by posted_at descending (newest first)
                    jobs_sorted = sorted(
                        jobs,
                        key=lambda j: j.get("posted_at", "") or "",
                        reverse=True,
                    )

                    st.session_state["jobs"] = jobs_sorted
                    st.session_state["last_scan"] = dt.datetime.now().isoformat()

                    st.success(
                        f"Found {len(jobs_sorted)} jobs (within ~{max_job_age_days} days)."
                    )

                    # Optionally auto-prepare applications
                    if auto_apply_toggle and uploaded_cv is not None:
                        auto_prep_count = 0
                        for job in jobs_sorted:
                            app_payload = build_application_payload(
                                job=job,
                                uploaded_cv=uploaded_cv,
                                profile=st.session_state["profile"],
                            )
                            st.session_state["applications"].append(app_payload)
                            auto_prep_count += 1
                        st.info(
                            f"Prepared {auto_prep_count} application payloads automatically."
                        )

                except Exception as e:
                    st.error(f"Error while searching jobs: {e}")

    st.markdown("### 📋 Job Feed (newest first)")

    jobs = st.session_state.get("jobs", [])
    if not jobs:
        st.info("No jobs yet. Click **Scan now** to fetch new postings.")
    else:
        for idx, job in enumerate(jobs):
            with st.container(border=True):
                top_cols = st.columns([4, 2])
                with top_cols[0]:
                    st.markdown(f"#### {job.get('title', 'Unknown Title')}")
                    st.markdown(
                        f"**Company:** {job.get('company', 'Unknown')}  "
                        f"• **Location:** {job.get('location', 'N/A')}  "
                        f"• **Type:** {job.get('type', 'N/A')}"
                    )
                with top_cols[1]:
                    posted_at = job.get("posted_at", "")
                    st.markdown(f"**Posted:** {posted_at or 'Unknown'}")
                    st.markdown(f"**Source:** {job.get('source', 'web')}")

                st.write(job.get("summary", ""))

                link = job.get("url")
                if link:
                    st.markdown(f"[🔗 Open original job post]({link})")

                col_a, col_b = st.columns([1, 1])
                with col_a:
                    if st.button(
                        "✨ Tailor resume & email just for this job",
                        key=f"tailor_{idx}",
                    ):
                        if uploaded_cv is None:
                            st.error(
                                "Please upload your base resume in the sidebar first."
                            )
                        else:
                            with st.spinner(
                                "Calling OpenAI to tailor resume & email..."
                            ):
                                try:
                                    app_payload = build_application_payload(
                                        job=job,
                                        uploaded_cv=uploaded_cv,
                                        profile=st.session_state["profile"],
                                    )
                                    st.session_state["applications"].append(app_payload)
                                    st.success(
                                        "Application payload added to queue "
                                        "(see 'Application Queue' tab)."
                                    )
                                except Exception as e:
                                    st.error(
                                        f"Failed to build application payload: {e}"
                                    )
                with col_b:
                    st.caption("Final submission is manual in this demo build.")

# ----- APPLICATION QUEUE TAB -----

with tab_queue:
    st.markdown("### 📨 Application Queue")
    apps = st.session_state.get("applications", [])

    if not apps:
        st.info(
            "No application payloads yet. Use **Tailor resume & email** from the Job Feed."
        )
    else:
        for idx, app in enumerate(apps):
            with st.expander(
                f"{idx+1}. {app['job'].get('title', 'Unknown Title')} @ "
                f"{app['job'].get('company', '')}"
            ):
                st.markdown("**Job link:** " + (app["job"].get("url") or "N/A"))
                st.markdown("---")
                st.markdown("#### Tailored email / message")
                st.code(app["email_body"], language="markdown")
                st.markdown("#### Tailored resume (Markdown)")
                st.code(app["tailored_resume_md"], language="markdown")

        # Allow user to download all applications as JSON for later tooling
        st.markdown("---")
        json_bytes = io.BytesIO(json.dumps(apps, indent=2).encode("utf-8"))
        st.download_button(
            "⬇️ Download all applications as JSON",
            data=json_bytes,
            file_name="applications_payload.json",
            mime="application/json",
        )
