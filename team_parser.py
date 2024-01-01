import bs4
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin
import concurrent.futures
from typing import BinaryIO, Literal
from dataclasses import dataclass
from utilities import download_logo

BASE_URLS_TO_PARSE = {'ru': 'https://premierliga.ru/', 'eng': 'https://eng.premierliga.ru/'}
CITY_PARAGRAPH_TITLES = {'ru': 'Город и год основания', 'eng': 'City and foundation year'}


@dataclass
class RawTeamInfo:
    id: int = None
    lang: str = None
    name: str = None
    city: str = None
    logo_src: str = None
    logo: str = None
    url: str = None

    def __str__(self):
        return f"id: {self.id}, name: {self.name}, city: {self.city}, logo: {self.logo_src}, url: {self.url}"


@dataclass
class TeamInfo:
    name: str = None
    city: str = None
    logo_src: str = None
    logo: str = None
    url: str = None
    name_eng: str = None
    city_eng: str = None
    url_eng: str = None

    def __str__(self):
        return f"id: {self.id}, name: {self.name} ({self.name_eng}), city: {self.city} ({self.city_eng}),\n" \
               f"logo_src: {self.logo_src}, url: {self.url} ({self.url_eng})"

    def to_dict(self) -> dict:
        return {
            'name': self.name, 'city': self.city, 'logo_src': self.logo_src, 'logo': self.logo, 'url': self.url,
            'name_eng': self.name_eng, 'city_eng': self.city_eng, 'url_eng': self.url_eng
        }


def cook_soup(url_to_parse: str) -> bs4.BeautifulSoup:
    text = requests.get(url_to_parse).text
    return BeautifulSoup(text, 'html.parser')


def generate_raw_team_info_list(lang: str) -> list[RawTeamInfo]:
    url_to_parse = BASE_URLS_TO_PARSE[lang]
    soup_to_parse = cook_soup(url_to_parse)
    teams_container = soup_to_parse.find(class_='rpl-clubs').find('tr')
    return [
        RawTeamInfo(id=num, lang=lang, name=t.a['title'], url=urljoin(url_to_parse, t.a['href']),
                    logo_src=t.img['src'], logo=download_logo(t.img['src']))
        for num, t in enumerate(teams_container)
    ]


def generate_raw_team_info_lists() -> list[RawTeamInfo]:
    langs = ('ru', 'eng')
    with concurrent.futures.ThreadPoolExecutor() as executor:
        raw_result = {lang: [] for lang in langs}
        futures = [executor.submit(generate_raw_team_info_list, lang) for lang in langs]
        for lang, future in zip(langs, concurrent.futures.as_completed(futures)):
            raw_result[lang] = future.result()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(parse_city_name, team, lang) for lang in raw_result for team in raw_result[lang]]
        result = [future.result() for future in concurrent.futures.as_completed(futures)]

    return result


def parse_city_name(team: RawTeamInfo, lang: str) -> RawTeamInfo:
    soup_to_parse = cook_soup(team.url)
    raw_parags = soup_to_parse.find('div', class_='main-info').find_all('p')
    clean_parags = tuple(tuple(i.strip() for i in p.text.strip().split('\n')) for p in raw_parags)

    city = None
    for p in clean_parags:
        city_paragraph_title = CITY_PARAGRAPH_TITLES[lang]
        if p[0] == city_paragraph_title:
            city = p[1].split(', ')[0]

    team.city = city
    return team


def combine_raw_lists(raw_team_info_list: list[RawTeamInfo]) -> list[dict]:
    team_info = {}
    for t in raw_team_info_list:
        if t.id not in team_info:
            team_info[t.id] = TeamInfo()
        if t.lang == 'ru':
            team_info[t.id].name = t.name
            team_info[t.id].city = t.city
            team_info[t.id].logo_src = t.logo_src
            team_info[t.id].logo = t.logo
            team_info[t.id].url = t.url
        else:
            team_info[t.id].name_eng = t.name
            team_info[t.id].city_eng = t.city
            team_info[t.id].url_eng = t.url

    result = [t.to_dict() for t in list(team_info.values())]
    return result


def main() -> list[dict]:
    raw_team_info_list = generate_raw_team_info_lists()
    team_info = combine_raw_lists(raw_team_info_list)
    return team_info

