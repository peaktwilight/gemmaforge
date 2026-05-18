#!/usr/bin/env bash
# Push kaggle/gemma4ge/gemma4ge.py to https://www.kaggle.com/code/peaktwilight/gemma4ge.
#
# The .py is jupytext percent format — runs as a script on Kaggle (the
# kernel is a script type, set in stone by Kaggle once created) AND
# converts cleanly to a Jupyter notebook locally for editing/sharing:
#
#   .venv-jupytext/bin/jupytext --to ipynb kaggle/gemma4ge/gemma4ge.py
#   .venv-jupytext/bin/jupytext --sync   kaggle/gemma4ge/gemma4ge.py  # keep both in step
#
# Source of truth is the .py.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KDIR="$REPO_ROOT/kaggle/gemma4ge"
JUPYTEXT="$REPO_ROOT/.venv-jupytext/bin/jupytext"

if [[ ! -x "$JUPYTEXT" ]]; then
  echo "jupytext not found at $JUPYTEXT" >&2
  echo "Bootstrap with:  python3.12 -m venv .venv-jupytext && .venv-jupytext/bin/pip install jupytext" >&2
  exit 1
fi

cd "$KDIR"

# Refresh the paired .ipynb so anyone reviewing the notebook off-Kaggle sees
# the latest source. Not pushed (it's gitignored), but handy locally.
echo "[push_kaggle_gemma4ge] jupytext --to ipynb gemma4ge.py"
"$JUPYTEXT" --to ipynb gemma4ge.py

echo "[push_kaggle_gemma4ge] kaggle kernels push -p $KDIR"
kaggle kernels push -p "$KDIR"

echo
echo "Pushed. Open: https://www.kaggle.com/code/peaktwilight/gemma4ge"
