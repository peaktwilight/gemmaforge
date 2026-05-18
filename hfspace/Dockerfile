FROM python:3.12-slim

WORKDIR /app

# Dashboard is stdlib-only. We do not install anything from requirements.txt
# at this stage; if a future revision streams Gemma from inside the Space
# we add the torch/transformers deps here.
COPY dashboard/ /app/dashboard/
COPY examples/ /app/examples/

# HuggingFace Spaces routes traffic to the port set by the $PORT env var,
# defaulting to 7860. The dashboard server takes --port.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "python -m dashboard.server --port ${PORT} --replay-events examples/events.ndjson --leads-file examples/leads.jsonl --replay-speedup 6"]
