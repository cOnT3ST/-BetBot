from dotenv import load_dotenv
import os
from urllib.parse import urljoin
import requests
from typing import Union

load_dotenv()
SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE")
STAT_API_KEY = os.getenv("STAT_API_KEY")
STAT_API_BASE_URL = 'https://api-football-beta.p.rapidapi.com'
STAT_API_HOST = 'api-football-beta.p.rapidapi.com'
HEADERS = {"X-RapidAPI-Key": STAT_API_KEY, "X-RapidAPI-Host": STAT_API_HOST}


class StatsAPIHandler:
    def __init__(self, year: Union[int, str]):
        self.league_id = "235"
        self.year = str(year)
        self.timezone = SCHEDULER_TIMEZONE

    def download_calendar(self):
        """
        Downloads a calendar of fixtures for the given season and league from the API.

        Returns:
        A JSON object representing the calendar of fixtures
        """

        endpoint = 'fixtures'
        next_year = str(int(self.year) + 1)
        querystring = {
            "to": f"{next_year}-07-01",
            "timezone": self.timezone,
            "season": self.year,
            "league": self.league_id,
            "from": f"{self.year}-07-01",
        }
        response = requests.get(
            urljoin(STAT_API_BASE_URL, endpoint),
            headers=HEADERS,
            params=querystring
        )

        return response.json()


sah = StatsAPIHandler(2023)
#sah.download_calendar()
