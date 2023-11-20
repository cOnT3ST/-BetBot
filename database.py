import sqlite3 as sq
from typing import List, Dict, Union, Callable, Any
import datetime
import json
from pprint import pprint


class Database:
    def __init__(self):
        self.name = 'db/MyRPLBetBot.db'

    @staticmethod
    def _ensure_connection(func: Callable):
        def wrapper(self, *args: Any, **kwargs: Any) -> Callable:
            with sq.connect(self.name) as conn:
                cur = conn.cursor()
                res = func(self, *args, **kwargs, conn=conn, cur=cur)
            return res

        return wrapper

    @_ensure_connection
    def _read_table_column_names(self, table_name: str, conn: sq.Connection, cur: sq.Cursor) -> list[str]:
        cur.execute(f"PRAGMA table_info({table_name})")
        rows = cur.fetchall()
        column_names = [row[1] for row in rows]
        return column_names

    @_ensure_connection
    def create_teams_table(self, conn: sq.Connection, cur: sq.Cursor):
        query = '''
		CREATE TABLE IF NOT EXISTS "teams" (
			"team_id"	INTEGER NOT NULL UNIQUE,
			"name"	TEXT,
			"city"	TEXT,
			"logo_url"	TEXT,
			"logo"	BLOB,
			PRIMARY KEY("team_id")
			)
		'''
        cur.execute(query)
        conn.commit()

    @_ensure_connection
    def _delete_table(self, table_name: str, conn: sq.Connection, cur: sq.Cursor):
        query = f"DROP TABLE IF EXISTS {table_name}"
        cur.execute(query)
        conn.commit()

    @_ensure_connection
    def _add_team(self, team: dict, conn: sq.Connection, cur: sq.Cursor):

        query = '''
		INSERT OR IGNORE INTO teams (team_id, name, city, logo_url, logo)
		VALUES(?, ?, ?, ?, ?)
		'''
        params = (team['team_id'], team['name'], team['city'], team['logo_url'], team['logo'])

        cur.execute(query, params)
        conn.commit()

    def update_teams_list(self, teams_to_check: List[Dict]):
        for t in teams_to_check:
            self._add_team(t)

    @_ensure_connection
    def create_contests_table(self, conn: sq.Connection, cur: sq.Cursor):
        query = '''
		CREATE TABLE IF NOT EXISTS "contests" (
		"contest_id"	INTEGER NOT NULL,
		"contest_api_id"	INTEGER,
		"league_name"	TEXT,
		"league_country"	TEXT,
		"year"	INTEGER,
		"start_date"	TEXT,
		"finish_date"	TEXT,
		"logo"	BLOB,
		"logo_url"	TEXT,
		"is_active"	INTEGER NOT NULL DEFAULT 1,
		PRIMARY KEY("contest_id" AUTOINCREMENT)
		)
		'''
        cur.execute(query)
        conn.commit()

    @_ensure_connection
    def add_contest(self, contest_api_id: int, league_name: str, league_country: str, year: int, start_date: str,
                    finish_date: str, logo: bytes, logo_url: str, is_active: bool, conn: sq.Connection,
					cur: sq.Cursor)\
			-> None:
        query = '''
		INSERT INTO contests
		(contest_api_id, league_name, league_country, year, start_date, finish_date, logo, logo_url, is_active)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		'''
        params = (contest_api_id, league_name, league_country, year, start_date, finish_date, logo, logo_url, is_active)
        cur.execute(query, params)
        conn.commit()

    @_ensure_connection
    def contest_exists(self, contest_api_id: int, year: int, conn: sq.Connection, cur: sq.Cursor) -> bool:

        query = "SELECT * FROM contests WHERE contest_api_id = ? AND year = ?"
        params = (contest_api_id, year)
        cur.execute(query, params)
        result = cur.fetchall()
        return result != []

    @_ensure_connection
    def read_contest(self, contest_id, conn: sq.Connection, cur: sq.Cursor):
        query = '''SELECT * FROM contests WHERE contest_id = ?'''
        params = (contest_id,)
        cur.execute(query, params)
        row_data = cur.fetchall()
        contest = dict(zip([c[0] for c in cur.description], row_data[0]))
        return contest

    @_ensure_connection
    def delete_contest(self, name: str, country: str, year: int, conn: sq.Connection, cur: sq.Cursor) -> None:
        if not self.contest_exists(name, country, year):
            return
        query = '''DELETE FROM contests WHERE name = ? AND country = ? AND year = ?'''
        params = (name, country, year)
        cur.execute(query, params)
        conn.commit()
        print(f'Сontest {name} {country} season {year} deleted')

    @_ensure_connection
    def create_matches_table(self, conn: sq.Connection, cur: sq.Cursor):
        query = '''
		CREATE TABLE IF NOT EXISTS "matches" (
		"match_id"	INTEGER NOT NULL UNIQUE,
		"contest_api_id"	INTEGER,
		"match_datetime"	TEXT,
		"round"	INTEGER,
		"home_team_id"	INTEGER,
		"away_team_id"	INTEGER,
		"score"	TEXT,
		"status_long"	TEXT,
		"status_short"	TEXT,
		FOREIGN KEY("contest_api_id") REFERENCES "contests"("contest_api_id"),
		PRIMARY KEY("match_id")
		)
		'''
        cur.execute(query)
        conn.commit()

    @_ensure_connection
    def _update_match(self, match: Dict[str, Union[str, int]], conn: sq.Connection, cur: sq.Cursor) -> None:
        query = '''
		INSERT INTO matches
		(match_id, contest_api_id, match_datetime, round, home_team_id, away_team_id, score, status_long, status_short)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		'''
        params = (
            match['match_id'], match['contest_api_id'], match['match_datetime'], match['round'], match['home_team_id'],
            match['away_team_id'], match['score'], match['status_long'], match['status_short']
        )
        cur.execute(query, params)
        conn.commit()

    def update_matches(self, matches_list: List[Dict]) -> None:
        for m in matches_list:
            self._update_match(m)

    @_ensure_connection
    def create_bets_table(self, conn: sq.Connection, cur: sq.Cursor) -> None:
        query = '''
        CREATE TABLE IF NOT EXISTS "bets" (
        "match_id"	INTEGER,
        "user_id"	INTEGER,
        "bet"	TEXT,
        FOREIGN KEY("user_id") REFERENCES "users"("user_id"),
        FOREIGN KEY("match_id") REFERENCES "calendar"("match_id")
        )
        '''
        cur.execute(query)
        conn.commit()

    @_ensure_connection
    def _delete_all_tables(self, conn: sq.Connection, cur: sq.Cursor) -> None:
        for t in ('contests', 'teams', 'matches', 'bets'):
            self._delete_table(t)



if __name__ == '__main__':
    from pprint import pprint

    db = Database()
    # for t in ('contests', 'bets', 'matches', 'teams'):
    #     db._delete_table(t)
    db._delete_all_tables()

