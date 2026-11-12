# Assignment Brief: Shop-Floor SOP Copilot

> Received from BiztelAI Technologies and kept here for reference. **Final deadline: Thursday, 12 November, 11:59 PM.**

Thank you for applying to BiztelAI. We liked your application and would like to invite you to the next step: a short assignment.

> We care more about how you think than how polished your code is. A simple, working solution with honest notes is better than a perfect-looking one.

## The scenario

A manufacturing plant has hundreds of SOPs, manuals and procedures as PDFs, covering quality, maintenance and safety. Supervisors on the shop floor need quick, reliable answers during their shifts, often from a phone or tablet.

You can download four sample documents from a fictional manufacturing plant, along with a few sample questions, from the [shared Drive folder](https://drive.google.com/drive/folders/1ruwt_m4H3nXRooPALppItfcC6oN63voR?usp=drive_link).

*In this repository the sample documents and questions are already included in [`Files/`](Files/).*

## What to do

1. **Understand the user.** Describe who the supervisor is, what they're trying to do, and what frustrates them today. No manufacturing experience is needed. You can use AI or any research to understand a shop-floor supervisor's role, and feel free to make reasonable assumptions as long as you state them clearly.

2. **User journey.** Using what you've learned, write how the supervisor would use an AI copilot, step by step, including what could go wrong. Please write this first draft yourself, before using AI, since the next step is to have AI challenge your thinking.

3. **AI challenge.** Ask an AI tool to critique your user journey as a skeptical user or product manager. Share the key parts of that conversation, and write a short reflection on what you agreed with, disagreed with, and changed.

4. **Build the copilot.** Build a simple working app (FastAPI + simple UI + RAG over the provided PDFs) where a supervisor can ask a question and get an answer from the documents, with the source document shown. If the answer isn't in the documents, the app should say so. Then add one improvement based on your user journey, and explain why you chose it.

5. **Deploy on your local network.** Run the app on your laptop and open it from another device on the same Wi-Fi, such as your phone.

6. **Final reflection (about one page).** What you'd build next, what you're unsure about, what you'd ask the customer, and what challenges you faced while building and deploying, and how you handled them.

Use the sample questions to test your app. Please also write **5 questions of your own**, including at least one the documents cannot answer, and include your app's answers in your README.

## Notes

- AI tools are allowed and encouraged. Just be ready to explain everything you submit.
- You can use any LLM. Running a small model locally (e.g., with Ollama) is a bonus but not required. A hosted API is fine if your laptop can't handle it.
- Docker is a bonus, not a requirement.
- Expected effort: around 5–6 hours.

## How to submit

We are reviewing submissions on a rolling basis and will schedule interviews as soon as we receive good submissions. The position may be filled before the deadline, so we encourage you to submit as early as you can.

Please reply to this message in the following format. **Incomplete submissions will not be reviewed.**

**A. GitHub repo link** (please make sure the repo is public) containing:

- Your code
- A README explaining how to set up and run the app, with your app's answers to your own 5 questions
- A `THINKING.md` file with these sections:
  - Understand the user
  - User journey
  - AI challenge (conversation excerpts and reflection)
  - The improvement you added, and why you chose it
  - Final reflection, including the biggest challenge you faced and how you handled it

**B. Screen recording link** (2–3 minutes, via Google Drive or Loom) showing:

- Your app answering 2 of the sample questions
- Your app responding to a question the documents cannot answer
- Your app opened and used from your phone

If anything is unclear, make a reasonable assumption and note it in `THINKING.md`.

Best regards,
Pugazh
BiztelAI Technologies

---

## Where each deliverable is in this repository

| Brief item | Where |
|---|---|
| Understand the user | [THINKING.md](THINKING.md), section 1 |
| User journey (my own first draft, then the revised one) | [THINKING.md](THINKING.md), section 2 |
| AI challenge: critique, my reflection, what I changed | [THINKING.md](THINKING.md), section 3 |
| The improvement I added and why (revision awareness) | [THINKING.md](THINKING.md), section 4 |
| Final reflection and biggest challenge | [THINKING.md](THINKING.md), section 5 |
| FastAPI app, RAG over the PDFs, source shown, "not found" handling | [`app/`](app/) |
| How to set up and run, phone access, my 5 questions with the app's answers | [README.md](README.md) |
| Sample questions, my own questions, evaluation and results | [`eval/`](eval/), [`Files/Sample_Questions.pdf`](Files/Sample_Questions.pdf) |
| Screenshots (desktop and phone) | [`screenshots/`](screenshots/) |
| Architecture reasoning | [FINAL_PLAN.md](FINAL_PLAN.md), [ARCHITECTURE.md](ARCHITECTURE.md), [ARCHITECTURE_Plan.md](ARCHITECTURE_Plan.md) |
| Screen recording | Linked in the submission reply, not stored in the repository |
