import os
import json
import re
from typing import List, Dict, Any

import requests
import streamlit as st


def _build_search_prompt(
    target_titles: str,
    locations: str,
    must_have_keywords: str,
    nice_to_have_keywords: str,
    max_age_hours: int,
    extra_query: str,
) -> str:
    return f"""
You are a job-search assistant bot.

Task:
Search the public web for **job postings** that match this profile, and then return ONLY a strict JSON list.

Profile:
- Target titles: {target_titles}
- Locations (including remote): {locations}
- Must-have keywords: {must_have_keywords}
- Nice-to-have keywords: {nice_to_have_keywords}
- Extra query / constraints: {extra_query}

Rules:
- Prefer jobs posted in the last {max_age_hours} hours (this may represent up to 2–3 weeks).
- Include **all roles that match the titles/keywords**: internships, entry-level, junior, mid, senior, contract, and full-time.
- Do NOT hide jobs because of level or employment type.
- Avoid / de-prioritize results whose main apply link is **LinkedIn** or **Dice**, but you may still include them if there are not enough others.
- For each job, you MUST return this JSON schema:

[
  {{
    "title": "...",
    "company": "...",
    "location": "...",
    "type": "Full-time / Internship / Contract / Other",
    "posted_at": "ISO8601 datetime string if known, else empty string",
    "summary": "2-3 sentences about the job",
    "url": "direct job posting URL (prefer company or ATS portals)",
    "source": "short label like 'Indeed', 'Company site', 'Wellfound', etc."
  }},
  ...
]

Important – output format:
- Your ENTIRE reply must be a **single JSON array** as above.
- Do NOT include any explanation, natural language, or reasoning.
- Do NOT include any `<think>` blocks or markdown fences.
- Reply with JSON only.
    """.strip()


def _extract_json_list(text: str) -> List[Dict[str, Any]]:
    """
    Try hard to pull a JSON array out of the model output.
    If no JSON array is found or parsing fails, return an empty list.
    """
    # Strip code fences if present
    if "```" in text:
        text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "").strip()

    # First, try direct parse
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return obj
    except Exception:
        pass

    # Fallback: grab the first [...] block
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []

    arr_text = m.group(0)

    try:
        obj = json.loads(arr_text)
    except Exception:
        return []

    if not isinstance(obj, list):
        return []

    return obj


def search_jobs_with_perplexity(
    target_titles: str,
    locations: str,
    must_have_keywords: str,
    nice_to_have_keywords: str,
    max_age_hours: int,
    max_results: int,
    extra_query: str,
) -> List[Dict[str, Any]]:
    """
    Calls Perplexity's chat completions API to perform a web-grounded job search
    and asks it to answer in structured JSON. If JSON can't be parsed, returns
    an empty list instead of crashing.
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY environment variable is not set.")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    prompt = _build_search_prompt(
        target_titles=target_titles,
        locations=locations,
        must_have_keywords=must_have_keywords,
        nice_to_have_keywords=nice_to_have_keywords,
        max_age_hours=max_age_hours,
        extra_query=extra_query,
    )

    payload = {
        "model": "sonar-reasoning",
        "messages": [
            {"role": "system", "content": "You are a helpful job search assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": False,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    raw_output = data["choices"][0]["message"]["content"]

    # Debug in UI so you can see what Perplexity is doing
    with st.expander("DEBUG: Raw Perplexity output", expanded=False):
        st.code(raw_output)

    jobs = _extract_json_list(raw_output)

    if not jobs:
        return []

    jobs = jobs[:max_results]

    for job in jobs:
        job["posted_at"] = job.get("posted_at") or ""

    return jobs
