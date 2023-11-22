import datetime
import time
from urllib.parse import urljoin
import requests
from typing import Union, List, Dict
from config import DEFAULT_COUNTRY, DEFAULT_LEAGUE
from load_confidential_data import load_confidentials_from_env
from pytz import timezone

CONFIDENTIAL_DATA = load_confidentials_from_env()
STAT_API_BASE_URL = 'https://api-football-beta.p.rapidapi.com'
STAT_API_HOST = 'api-football-beta.p.rapidapi.com'
HEADERS = {"X-RapidAPI-Host": STAT_API_HOST, "X-RapidAPI-Key": CONFIDENTIAL_DATA['stat_api_key']}


class StatsAPI:
    def __init__(self):
        self.timezone = timezone(CONFIDENTIAL_DATA['scheduler_timezone'])
        # TODO add a counter for requests per day, erase it every day, keep in mind permitted
        # requests per day by stats service

    def _make_request(self, endpoint: str, params: dict[str, Union[str, int]] = None) \
            -> Union[None, dict]:
        """
        Makes request to a certain endpoint of the API stats server

        :param endpoint: API endpoint
        :param params: A set of parameters required for this particular request
        :return:
        """

        if not isinstance(endpoint, str):
            raise ValueError('Endpoint must be a string')

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

        response = requests.get(request_url, headers=HEADERS, params=params)

        if not response.ok:
            print('Request failed')
            return None

        valued_data = response.json()
        print('Response ok. Data obtained')
        return valued_data

    def country_supported(self, country_name: str) \
            -> bool:
        """
        Checks if a certain country is supported by the stats API
        :return: True if country is supported, False otherwise
        """

        # TODO add supported countries to DB or cache to avoid excessive API requests and update it once per week
        if not isinstance(country_name, str):
            raise ValueError('Country parameter must only be string')

        response = self._make_request(
            endpoint='countries',
            params={'name': country_name}
        )

        result = response['results'] != 0
        return result

    def determine_current_season(self) -> Union[None, Dict[str, Union[str, int]]]:
        """
        Determines the details of the current season for a football league.

        Returns a dictionary containing the details of the current season, or None if the league hasn't started yet.

        Returns:
            Union[None, Dict[str, Union[str, int]]]: A dictionary with the following keys:
                - 'contest_api_id' (int): The API ID of the current season.
                - 'league_name' (str): The name of the league.
                - 'league_country' (str): The country of the league.
                - 'year' (int): The year of the current season.
                - 'start_date' (str): The start date of the current season.
                - 'end_date' (str): The end date of the current season.
                - 'logo_url' (str): The URL of the league's logo.
                - 'logo' (bytes): The downloaded logo image data.
            If the league hasn't started yet, None is returned.

        """

        league_country = DEFAULT_COUNTRY
        league_name = DEFAULT_LEAGUE

        response = self._make_request(
            endpoint='leagues',
            params={
                'name': league_name,
                'current': 'true',
                'country': league_country
            }
        )

        if response['results'] == 0:  # League hasn't started yet
            return None

        season_id = response['response'][0]['league']['id']
        logo_url = response['response'][0]['league']['logo']
        logo = self._download_logo(logo_url)
        season_data = response['response'][0]['seasons'][0]

        return {
            'contest_api_id': season_id,
            'league_name': league_name,
            'league_country': league_country,
            'year': season_data['year'],
            'start_date': season_data['start'],
            'finish_date': season_data['end'],
            'logo_url': logo_url,
            'logo': logo,
            'is_active': True
        }

    def get_calendar(self, contest: Dict[str, Union[str, int]]) -> List[Dict]:
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
                "league": contest['contest_api_id']
            }
        )

        raw_matches_data = response['response']
        matches = [
            {
                'match_id': m['fixture']['id'],
                'contest_api_id': contest['contest_api_id'],
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

    def get_all_teams(self, contest_api_id: int, year: int) \
            -> List[Dict[str, Union[str, bytes]]]:
        """Gets a list of teams to participate in this football tournament."""

        response = self._make_request(
            endpoint='teams',
            params={
                "league": contest_api_id,
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
            logo = self._download_logo(logo_url)
            result.append({'team_id': team_id, 'name': name, 'city': city, 'logo': logo, 'logo_url': logo_url})

        return result

    def _download_logo(self, url: str) -> bytes:
        response = requests.get(url)
        if not response.ok:
            # Get default logo
            with open('db/Images/no logo.png', 'rb') as file:
                return file.read()
        return response.content


if __name__ == '__main__':
    from pprint import pprint
    sa = StatsAPI()
