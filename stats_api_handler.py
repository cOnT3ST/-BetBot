import datetime

from dotenv import load_dotenv
import os
from urllib.parse import urljoin
import requests
from typing import Union
from config import DEFAULT_COUNTRY
from pytz import timezone

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

    def get_contest(
            self,
            country: str = DEFAULT_COUNTRY,
            year: int = datetime.datetime.now(tz=timezone(SCHEDULER_TIMEZONE)).year
    ):
        endpoint = 'leagues'
        querystring = {"season": year, "country": country}
        response = requests.get(urljoin(STAT_API_BASE_URL, endpoint), headers = HEADERS, params = querystring)
        valued_data = response.json()['response']
        return valued_data


    def _download_matches_info(self, round_id=None):
        """
        Downloads match information from the API endpoint 'fixtures' for a given round ID.

        :param round_id: (optional) The ID of the round to download match information for.
        :return: The JSON response containing the match information for the given round ID.
        """
        endpoint = 'fixtures'
        next_year = str(int(self.year) + 1)
        querystring = {
            "from": f"{self.year}-07-01",
            "to": f"{next_year}-07-01",
            "timezone": self.timezone,
            "season": self.year,
            "league": self.league_id,
            "round": round_id if not round_id else f"Regular Season - {str(round_id)}"
        }
        response = requests.get(
            urljoin(STAT_API_BASE_URL, endpoint),
            headers=HEADERS,
            params=querystring
        )
        valued_data = response.json()['response']
        return valued_data

    def download_all_matches(self):
        """
        Downloads all match information for the current season and league.

        :return: The JSON response containing the match information for the current season and league.
        """
        return self._download_matches_info()

    def download_matches_by_round(self, round_id: int):
        """
        Downloads match information for a specific round of the current season and league.

        :param round_id: The ID of the round to download match information for.
        :return: The JSON response containing the match information for the specified round.
        """
        return self._download_matches_info(round_id=round_id)



sah = StatsAPIHandler(2023)
#print(sah.get_contest())
#print(sah.download_all_matches())

# with open('fixtures_response.txt', mode='w', encoding='utf-8') as f:
#     json.dump(data_to_dump, f, indent=4, ensure_ascii=False)
