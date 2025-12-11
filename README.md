
# AutoApply AI – Streamlit Job Application Copilot

This is a **demo Streamlit web app** that:

- Uses the **Perplexity API** to search the web for fresh job postings (tries to avoid LinkedIn/Dice links).
- Prioritizes jobs posted within a configurable number of hours (default: 48 hours).
- Uses the **OpenAI API** to:
  - Tailor your resume text to each job.
  - Generate a short application email / message.
- Keeps an **Application Queue** where you can review & download all tailored applications.

⚠️ **Important:** This project does **NOT** auto‑submit forms to company portals.  
Instead, it prepares high‑quality tailored content. You are responsible for final submission,
or you can integrate `backend/apply_bot.py` with your own automation (email sender, ATS API, browser bot, etc.).

## Project structure

- `app.py` – Streamlit UI.
- `backend/job_sources.py` – Perplexity job search integration.
- `backend/resume_tailor.py` – OpenAI resume + email generation.
- `backend/apply_bot.py` – builds an application payload; extend this for full automation.
- `requirements.txt` – Python dependencies.

## Setup

1. Create & activate a virtual environment (Python 3.10+ recommended).
2. Install packages:

```bash
pip install -r requirements.txt
```

3. Set your API keys as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export PERPLEXITY_API_KEY="pplx-..."
```

(Or paste them in the Streamlit sidebar each time you run the app.)

4. Run the app:

```bash
streamlit run app.py
```

Then open the local URL shown in the terminal.

## Usage

1. In the sidebar:
   - Paste your OpenAI and Perplexity API keys.
   - Set your target titles, locations, and keywords.
   - Upload your base resume (PDF or TXT).
   - Optionally enable "Automatically prepare applications for all new jobs".

2. In **Job Feed**:
   - Click **Scan now** to fetch new job postings.
   - Review job cards and click **Tailor resume & email** for any job you like.

3. In **Application Queue**:
   - Review tailored resumes and emails.
   - Download all of them as a JSON file for further automation.

You can customize prompts and logic in the `backend/` folder to better fit your profile or country‑specific rules.
