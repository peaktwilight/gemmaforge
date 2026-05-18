FROM python:3.12-slim

# Install Node 20 + git (needed to clone + build pwnkit-cli) and minimal
# build deps. esbuild bundles natively so we don't need a C toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl ca-certificates gnupg sqlite3 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g pnpm@9

WORKDIR /app

# Pwnkit lives at /opt/pwnkit, built from the patched branch on
# PwnKit-Labs/pwnkit that adds OPENAI_BASE_URL / OPENAI_MODEL support to
# the API runtime (so we can point it at OpenRouter for Gemma 4 31B).
RUN git clone --depth 1 --branch claude/fix-types-for-gemmaforge-build \
        https://github.com/PwnKit-Labs/pwnkit.git /opt/pwnkit \
    && cd /opt/pwnkit \
    && pnpm install --frozen-lockfile \
    && pnpm --filter @pwnkit/shared build \
    && pnpm --filter @pwnkit/core build \
    && pnpm --filter pwnkit-cli build \
    && rm -rf /opt/pwnkit/node_modules/.cache /root/.npm /root/.local /root/.cache

ENV PWNKIT_CLI=/opt/pwnkit/packages/cli/dist/index.js
ENV PWNKIT_DB=/tmp/pwnkit.db

COPY dashboard/ /app/dashboard/
COPY examples/ /app/examples/

ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "python -m dashboard.server --port ${PORT} --replay-events examples/events.ndjson --leads-file examples/leads.jsonl --pwnkit-replay examples/pwnkit-events.ndjson --pwnkit-cli ${PWNKIT_CLI} --pwnkit-db ${PWNKIT_DB} --replay-speedup 6"]
