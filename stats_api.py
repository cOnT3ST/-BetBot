import datetime
import logging
from utilities import initialize_logging, load_confidentials_from_env, download_logo
from urllib.parse import urljoin
import requests
from typing import List, Dict
from config import SCHEDULER_TIMEZONE, PREFERRED_DATETIME_FORMAT
from pytz import timezone
from database import Database

STAT_API_BASE_URL = 'https://api-football-beta.p.rapidapi.com'
STAT_API_HOST = 'api-football-beta.p.rapidapi.com'
HEADERS = {"X-RapidAPI-Host": STAT_API_HOST, "X-RapidAPI-Key": load_confidentials_from_env("STAT_API_KEY")}

initialize_logging()


class StatsAPIHandler:
    def __init__(self):
        self.timezone = timezone(SCHEDULER_TIMEZONE)
        self.db = Database()
        # TODO add a counter for requests per day, erase it every day, keep in mind permitted
        # TODO requests per day by stats service

    def _make_request(self, endpoint: str, params: dict[str, str | int] = None) -> None | dict:
        """
        Makes request to a certain endpoint of the API stats server

        :param endpoint: API endpoint
        :param params: A set of parameters required for this particular request
        :return:
        """

        if not isinstance(endpoint, str):
            raise ValueError('Endpoint must be a string')

        requests_today = self.db.read_requests_counter()
        if requests_today == 100:
            return

        request_url = urljoin(base=STAT_API_BASE_URL, url=endpoint)
        # request_url = "https://www.amazon.com/nothing_here"
        # request_url = 'https://dadsasdasdsd.com/'
        # request_url = 'https://api.github.com/'
        # try:
        # response = requests.get(request_url, headers=HEADERS, params=params)
        # try:
        #     response = requests.get('https://geeksforgeeks.org/naveen/')
        #     response.raise_for_status()
        # except requests.ConnectionError as e:
        #     print(e.args[0])
        # except requests.HTTPError as e:
        #     print(e.args[0])
        # except requests.TooManyRedirects as e:
        #     print(e.args[0])
        # except requests.ReadTimeout as e:
        #     print(e.args[0])
        # except requests.Timeout as e:
        #     print(e.args[0])
        # except requests.JSONDecodeError as e:
        #     print(e.args[0])

        logging.info(f"Requesting {request_url} with params: {params}...")
        response = requests.get(request_url, headers=HEADERS, params=params)
        self.db.increment_requests_counter()

        if not response.ok:
            logging.error('BAD RESPONSE')
            return None

        logging.info(f"Request successful")
        valued_data = response.json()
        return valued_data

    def country_supported(self, country_name: str) -> bool:
        """
        Checks if a certain country is supported by the stats API
        :return: True if country is supported, False otherwise
        """

        # TODO add supported countries to DB or cache to avoid excessive API requests and update it once per week
        if not isinstance(country_name, str):
            raise ValueError('Country parameter must only be string')

        logging.info(f'Checking if country ({country_name}) supported by STATS API ...')
        response = self._make_request(endpoint='countries', params={'name': country_name})

        result = response['results'] != 0
        logging.info(f'Country supported: {result}')
        return result

    def get_current_season(self, league_country, league_name) -> None | Dict[str, str | int]:
        """
        Gets the details of the current season for a football league.

        Returns a dictionary containing the details of the current season, or None if the league hasn't started yet.

        Returns:
            Union[None, Dict[str, Union[str, int]]]: A dictionary with the following keys:
                - 'season_api_id' (int): The API ID of the current season.
                - 'league_name' (str): The name of the league.
                - 'league_country' (str): The country of the league.
                - 'year' (int): The year of the current season.
                - 'start_date' (str): The start date of the current season.
                - 'end_date' (str): The end date of the current season.
                - 'logo_url' (str): The URL of the league's logo.
                - 'logo' (bytes): The downloaded logo image data.
                - 'creation_datetime' (str): The date and time data was stored into DB.
                - 'is_active' (bool): Represents if this season is still active.
            If the league hasn't started yet, None is returned.

        """

        response = self._make_request(endpoint='leagues',
                                      params={'name': league_name, 'current': 'true', 'country': league_country}
                                      )

        if response['results'] == 0:  # League hasn't started yet
            return None

        season_id = response['response'][0]['league']['id']
        logo_url = response['response'][0]['league']['logo']
        logo = download_logo(logo_url)
        season_data = response['response'][0]['seasons'][0]

        return {
            'season_api_id': season_id,
            'league_name': league_name,
            'league_country': league_country,
            'year': season_data['year'],
            'start_date': season_data['start'],
            'finish_date': season_data['end'],
            'logo_url': logo_url,
            'logo': logo,
            'creation_datetime': datetime.datetime.now().strftime(PREFERRED_DATETIME_FORMAT),
            'is_active': True
        }

    def get_calendar(self, contest: Dict[str, str | int]) -> list[dict]:
        """Get the match calendar for a contest.

        Args:
            contest (dict): Contest details including API ID, season, etc.

        Returns:
            list: List of dictionaries containing match details.

        """

        response = self._make_request(
            endpoint='fixtures',
            params={
                "from": contest['start_date'],
                "to": contest['finish_date'],
                "timezone": self.timezone.zone,
                "season": contest['year'],
                "league": contest['season_api_id']
            }
        )

        raw_matches_data = response['response']
        matches = [
            {
                'match_id': m['fixture']['id'],
                'season_api_id': contest['season_api_id'],
                'match_datetime': m['fixture']['date'],
                'round': int(m['league']['round'].split(' - ')[-1]),
                'home_team_id': m['teams']['home']['id'],
                'away_team_id': m['teams']['away']['id'],
                'score': f"{m['goals']['home']}-{m['goals']['away']}",
                'status_long': m['fixture']['status']['long'],
                'status_short': m['fixture']['status']['short']
            }
            for m in raw_matches_data
        ]
        return matches

    def get_league_teams(self, season_api_id: int, year: int) -> List[Dict[str, str | bytes]]:
        """Gets a list of teams to participate in this football tournament."""

        response = self._make_request(
            endpoint='teams',
            params={
                "league": season_api_id,
                "season": year
            }
        )

        teams_list = response['response']
        result = []
        for t in teams_list:
            team_id = t['team']['id']
            name = t['team']['name']
            city = t['venue']['city']
            logo_url = t['team']['logo']
            logo = download_logo(logo_url)
            result.append({'team_id': team_id, 'name': name, 'city': city, 'logo': logo, 'logo_url': logo_url})

        return result


if __name__ == '__main__':
    from pprint import pprint

    sa = StatsAPIHandler()
