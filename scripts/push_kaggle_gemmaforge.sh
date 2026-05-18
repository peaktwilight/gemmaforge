#!/usr/bin/env bash
# Push kaggle/gemmaforge/gemmaforge.py to https://www.kaggle.com/code/peaktwilight/gemmaforge.
#
# The .py is jupytext percent format — runs as a script on Kaggle (the
# kernel is a script type, set in stone by Kaggle once created) AND
# converts cleanly to a Jupyter notebook locally for editing/sharing:
#
#   .venv-jupytext/bin/jupytext --to ipynb kaggle/gemmaforge/gemmaforge.py
#   .venv-jupytext/bin/jupytext --sync   kaggle/gemmaforge/gemmaforge.py  # keep both in step
#
# Source of truth is the .py.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KDIR="$REPO_ROOT/kaggle/gemmaforge"
JUPYTEXT="$REPO_ROOT/.venv-jupytext/bin/jupytext"

if [[ ! -x "$JUPYTEXT" ]]; then
  echo "jupytext not found at $JUPYTEXT" >&2
  echo "Bootstrap with:  python3.12 -m venv .venv-jupytext && .venv-jupytext/bin/pip install jupytext" >&2
  exit 1
fi

cd "$KDIR"

# Refresh the paired .ipynb so anyone reviewing the notebook off-Kaggle sees
# the latest source. Not pushed (it's gitignored), but handy locally.
echo "[push_kaggle_gemmaforge] jupytext --to ipynb gemmaforge.py"
"$JUPYTEXT" --to ipynb gemmaforge.py

echo "[push_kaggle_gemmaforge] kaggle kernels push -p $KDIR"
kaggle kernels push -p "$KDIR"

echo
echo "Pushed. Open: https://www.kaggle.com/code/peaktwilight/gemmaforge"
