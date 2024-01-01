import logging
import os
from dotenv import load_dotenv
import requests


def load_confidentials_from_env(conf_data_to_load: str) -> str | None:
    load_dotenv()
    return os.getenv(conf_data_to_load)


def initialize_logging():
    logging.basicConfig(
        level=logging.INFO,
        filename="MyRPLBetBot.log",
        format="%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
        datefmt="%d.%m.%Y %H:%M:%S",
        encoding='UTF-8'
    )


def download_logo(url: str) -> bytes:
    response = requests.get(url)
    if not response.ok:
        # Get default logo
        with open('db/Images/no logo.png', 'rb') as file:
            return file.read()
    return response.content
