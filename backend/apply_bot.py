from typing import Dict, Any

from .resume_tailor import generate_tailored_resume_and_email


def build_application_payload(
    job: Dict[str, Any],
    uploaded_cv,
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """
    High-level helper:
    - Calls OpenAI to tailor resume + email.
    - Returns a dict that can later be used by a real "applier"
      (e.g. email sender, Selenium bot, Greenhouse/Lever API client, etc.)
    """
    tailored_resume_md, email_body = generate_tailored_resume_and_email(
        job=job,
        uploaded_cv=uploaded_cv,
        profile=profile,
    )

    payload: Dict[str, Any] = {
        "job": job,
        "email_body": email_body,
        "tailored_resume_md": tailored_resume_md,
        # Hooks for further automation:
        "target_email": None,  # you can populate this if you parse company emails
        "source_system": job.get("source", "web"),
    }
    return payload
