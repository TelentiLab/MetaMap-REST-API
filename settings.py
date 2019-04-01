from dotenv import load_dotenv
from pathlib import Path

# explicitly providing path to '.env'
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)
