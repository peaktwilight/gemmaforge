# Submission Runbook — Gemma 4 Good Hackathon

Operational drill-down for submission day. `SUBMISSION.md` is the high-level checklist; this file says exactly what to run and in what order. Times are minutes before the 23:59 UTC deadline.

## T-30 min — pre-flight

1. **Repo clean and synced.**
   ```bash
   git status                  # must be clean
   git pull --rebase origin main   # absorb any of Efe's late commits
   ```
2. **HF Space is RUNNING.**
   ```bash
   curl -sL https://huggingface.co/api/spaces/peaktwilight/gemmaforge | jq '.runtime.stage'
   ```
   Expect `"RUNNING"`. Anything else (`BUILDING`, `BUILD_ERROR`, `STOPPED`) → see Failure modes below.
3. **Local streaming server boots cleanly.**
   ```bash
   source .venv/bin/activate
   python -m src.stream_with_probe --serve
   ```
   Wait for `listening on http://0.0.0.0:8787/`. Open the URL in a browser, click one of the preset prompts, confirm tokens stream out coloured (green/yellow/red).
4. **Writeup word count is under the 1500-word cap.**
   ```bash
   wc -w WRITEUP.md
   ```

## T-15 min — flip GitHub repo public

```bash
gh repo edit peaktwilight/gemmaforge --visibility public
gh repo view peaktwilight/gemmaforge --json visibility
```

The visibility field must read `"PUBLIC"`. Hackathon rules require it.

## T-10 min — paste Kaggle Writeup

1. Open https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups
2. Click **New Writeup**.
3. **Title:** `GemmaForge — Catch Vulnerabilities Inside Gemma 4, Before the Token Lands`
4. **Track:** **Main Track**. Also tick **Safety & Trust** and **Ollama** if the UI lets you stack the impact/special-tech prizes.
5. Paste the full content of `WRITEUP.md` into the body.
6. Attach:
   - Cover image: `web/cover.svg`
   - Code repo URL: `https://github.com/peaktwilight/gemmaforge`
   - Video URL: YouTube link (unlisted-to-public on submission day)
   - Live demo URL: `https://huggingface.co/spaces/peaktwilight/gemmaforge`

## T-5 min — hit Submit on Kaggle

1. Click the **Submit** button (top right of the writeup editor).
2. Wait for the green confirmation banner.
3. Take a screenshot of the confirmation page and drop it in `docs/` for your records.

## T+0 — announce

1. Paste the content of `LINKEDIN.md` into a new LinkedIn post.
2. Put the Kaggle writeup URL in the **first comment** (per Doruk's posting preferences — link goes in comments, not in the body).

## Failure modes

- **HF Space in `BUILD_ERROR` right before submission.** Fall back: the "Live Demo" link in the Kaggle writeup points to the GitHub repo. Add a one-line note in the writeup body: "If the Space is rebuilding, run `python -m src.stream_with_probe --serve` from the repo." Embed the GIF from `docs/` as a visual.
- **Forgot to flip the repo public.** Submission rules require it. Re-run `gh repo edit peaktwilight/gemmaforge --visibility public`, confirm with `gh repo view`, then re-attach the repo URL on the Kaggle writeup and click **Submit** again.
- **Video isn't ready.** Upload an unlisted YouTube placeholder so the URL exists, then swap the visibility to public after the deadline. If you don't even have that, screen-record the local server (the same `--serve` flow above) with OBS or QuickTime as a stopgap.
- **Kaggle returns a 502 or the Submit button is missing.** Screenshot the writeup in its current state. Wait 60 seconds. Retry. If still failing, contact the hackathon organizers via the Discord link on the Kaggle competition page.
