import os
from typing import Dict, Any, Tuple

from openai import OpenAI


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=api_key)


def _read_cv_file(uploaded_cv) -> str:
    """
    uploaded_cv is a Streamlit UploadedFile. We support text or PDF.
    Use getvalue() so it can be read multiple times.
    """
    import io

    if uploaded_cv is None:
        return ""

    name = uploaded_cv.name.lower()
    raw_bytes = uploaded_cv.getvalue()  # safe multiple reads

    if name.endswith(".txt"):
        return raw_bytes.decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts)
        except Exception:
            return ""

    # fallback
    return raw_bytes.decode("utf-8", errors="ignore")


def generate_tailored_resume_and_email(
    job: Dict[str, Any],
    uploaded_cv,
    profile: Dict[str, Any],
) -> Tuple[str, str]:
    """
    Returns (tailored_resume_markdown, email_body_markdown)
    """
    client = _get_client()
    base_cv_text = _read_cv_file(uploaded_cv)

    system_prompt = """
You are an expert resume writer for STEM students on OPT in the USA.

Your job:
1. Read the candidate's base resume.
2. Read the job description / summary.
3. Produce a **tailored resume in Markdown** that:
   - keeps all truthful information,
   - re-orders bullets & sections to match the job,
   - rewrites bullets to mirror the job description language without lying,
   - highlights skills and tools from the job description that the candidate actually has.

Rules:
- Do not invent experience, degrees, companies, or technologies.
- You may reword or merge bullets for clarity and impact.
- Keep the resume to 1–2 pages worth of text.
- The resume must be valid GitHub-flavored Markdown.
    """.strip()

    user_prompt_resume = f"""
Candidate profile summary (free text from sidebar):
{profile.get("profile_summary", "")}

Base resume (raw text):
\"\"\""
{base_cv_text}
\"\"\""

Job info:
- Title: {job.get("title", "")}
- Company: {job.get("company", "")}
- Location: {job.get("location", "")}
- Type: {job.get("type", "")}
- Job summary:
{job.get("summary", "")}

Now output ONLY the tailored resume in Markdown, no explanation.
    """.strip()

    resume_resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_resume},
        ],
        temperature=0.4,
        max_tokens=2000,
    )
    tailored_resume_md = resume_resp.choices[0].message.content

    email_system_prompt = """
You are writing a concise, friendly job application email.

Write a short email / message that:
- addresses the hiring manager (use a generic greeting if no name),
- mentions the role and company,
- highlights 3–5 points from the candidate's profile that match the job,
- has a clear closing line and call-to-action.

Do NOT mention visa details unless the user explicitly asked you to.
Return plain text or Markdown, no extra commentary.
    """.strip()

    email_user_prompt = f"""
Candidate profile:
{profile.get("profile_summary", "")}

Relevant keywords (must-have):
{profile.get("must_have_keywords", "")}

Job info:
- Title: {job.get("title", "")}
- Company: {job.get("company", "")}
- Location: {job.get("location", "")}
- Type: {job.get("type", "")}
- Job summary:
{job.get("summary", "")}

Write the email now.
    """.strip()

    email_resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": email_system_prompt},
            {"role": "user", "content": email_user_prompt},
        ],
        temperature=0.5,
        max_tokens=600,
    )
    email_body = email_resp.choices[0].message.content

    return tailored_resume_md, email_body
