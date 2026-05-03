from dotenv import load_dotenv
from core import run_forever

if __name__ == "__main__":
    load_dotenv()
    run_forever(poll_interval=30)
