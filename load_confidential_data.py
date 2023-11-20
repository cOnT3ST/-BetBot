import os
from dotenv import load_dotenv


def load_confidentials_from_env():
    load_dotenv()

    scheduler_timezone: str = os.getenv("SCHEDULER_TIMEZONE")
    stat_api_key = os.getenv("STAT_API_KEY")

    return {
        'scheduler_timezone': scheduler_timezone,
        'stat_api_key': stat_api_key
    }
