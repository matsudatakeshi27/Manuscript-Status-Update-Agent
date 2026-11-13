
from pathlib import Path
from platformdirs import user_data_dir

# Source directory
APP_DIR = Path(__file__).resolve().parent

# Main project directory
PROJECT_DIR = APP_DIR.parent

# Private application data directory
DATA_DIR = Path(
    user_data_dir("ScholarOneMonitor", appauthor=False)
)

# Private configuration and data
CONFIG_FILE = DATA_DIR / "config.json"
ENV_FILE = DATA_DIR / ".env"
DATABASE_FILE = DATA_DIR / "manuscripts.json"
RESULTS_FILE = DATA_DIR / "browser_results.json"

# Private logs
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "monitor.log"
ERROR_LOG_FILE = LOG_DIR / "monitor_error.log"

# Create required directories
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
