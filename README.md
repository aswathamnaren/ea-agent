# One-time setup
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Every time you want to run the agent
$env:PYTHONUTF8 = "1"
python main.py