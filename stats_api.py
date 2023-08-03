import datetime

from dotenv import load_dotenv
import os
from urllib.parse import urljoin
import requests
from typing import Union
from config import DEFAULT_COUNTRY, DEFAULT_LEAGUE
from pytz import timezone
from pprint import pprint

load_dotenv()
SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE")
STAT_API_KEY = os.getenv("STAT_API_KEY")
STAT_API_BASE_URL = 'https://api-football-beta.p.rapidapi.com'
STAT_API_HOST = 'api-football-beta.p.rapidapi.com'
HEADERS = {"X-RapidAPI-Key": STAT_API_KEY, "X-RapidAPI-Host": STAT_API_HOST}


class StatsAPI:
    def __init__(self):
        self.timezone = timezone(SCHEDULER_TIMEZONE)

    def get_contest_info(self,
                         country: str = DEFAULT_COUNTRY,
                         league: str = DEFAULT_LEAGUE,
                         year: int = None
                         ) -> Union[dict, None]:
        if not year:
            year = datetime.datetime.now(tz=self.timezone).year
        endpoint = 'leagues'
        querystring = {"country": country, "name": league, "season": year}
        response = requests.get(urljoin(STAT_API_BASE_URL, endpoint), headers=HEADERS, params=querystring)
        valued_data = response.json()['response'][0]
        return valued_data if not valued_data == [] else None

    # def get_matches_info(
    #         self,
    #         league_api_id: int,
    #         year: int,
    #         round_id=None
    # ):
    #     endpoint = 'fixtures'
    #     next_year = year + 1
    #     querystring = {
    #         "from": f"{year}-07-01",
    #         "to": f"{next_year}-07-01",
    #         "timezone": self.timezone,
    #         "season": year,
    #         "league": league_api_id,
    #         "round": round_id if not round_id else f"Regular Season - {str(round_id)}"
    #     }
    #     response = requests.get(
    #         urljoin(STAT_API_BASE_URL, endpoint),
    #         headers=HEADERS,
    #         params=querystring
    #     )
    #     valued_data = response.json()['response']
    #     return valued_data
    #
    # def get_all_contest_matches(self, league_api_id: int, year: int) -> list:
    #     return self.get_matches_info(league_api_id, year)
    #
    # def get_contest_matches_by_round(self, league_api_id: int, year: int, round_id: int) -> list:
    #     return self.get_matches_info(league_api_id, year, round_id)


if __name__ == '__main__':
    sah = StatsAPI()
    pprint(sah.get_contest_info())
