import pprint
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
	def add_contest(self, contest_api_id: int, name: str, country: str, year: int, start_datetime: str,
					finish_datetime: str, logo: str, is_active, conn: sq.Connection, cur: sq.Cursor) -> None:
		if self.contest_exists(name, country, year):
			return

		query = '''
		INSERT INTO contests
		(api_id, name, logo, country, year, start_datetime, finish_datetime, logo, is_active)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
		'''
		params = (contest_api_id, name, logo, country, year, start_datetime, finish_datetime, logo, is_active)
		cur.execute(query, params)
		conn.commit()

	@_ensure_connection
	def contest_exists(self, name: str, country: str, year: int, conn: sq.Connection, cur: sq.Cursor) -> bool:
		"""
		Checks if content already exists in the database.
		"""
		query = "SELECT * FROM contests WHERE name = ? AND country = ? AND year = ?"
		params = (name, country, year)
		cur.execute(query, params)
		result = cur.fetchall()
		return result != []

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
	def read_contest(self, id: int, conn: sq.Connection, cur: sq.Cursor) -> Union[tuple, None]:
		query = '''SELECT * FROM contests WHERE id = ?'''
		params = (id,)
		cur.execute(query, params)
		res = cur.fetchone()
		return res

	# @_ensure_connection
	# def get_users(self, conn, cur) -> List:
	# 	query = "SELECT * FROM users"
	# 	cur.execute(query)
	# 	db_data = cur.fetchall()
	# 	return [
	# 		{
	# 			'id': user[0],
	# 			'first_name': user[1],
	# 			'last_name': user[2],
	# 			'telegram_id': user[3],
	# 			'is_admin': True if user[4] == 1 else False,
	# 			'contest': None
	# 		}
	# 		for user in db_data
	# 	]
	#
	# @_ensure_connection
	# def get_contests(self, conn, cur):
	# 	query = "SELECT * FROM contest"
	# 	cur.execute(query)
	# 	db_data = cur.fetchall()
	# 	return [
	# 		{
	# 			'id': contest[0],
	# 			'api_id': contest[1],
	# 			'name': contest[2],
	# 			'country': contest[3],
	# 			'year': contest[4],
	# 			'start_datetime': contest[5],
	# 			'finish_datetime': contest[6],
	# 			'logo': contest[7],
	# 			'is_active': True if contest[8] == 1 else False
	# 		}
	# 		for contest in db_data
	# 	]
	# #[(2, 235, None, None, 2023, None, None, None, 0)]

	# def add_calendar(self, data: List[Dict], contest_id=1):
	# 	# res = []
	# 	with sq.connect(self.name) as conn:
	# 		cur = conn.cursor()
	# 		for match in data:
	# 			match_id = match['fixture']['id']
	# 			match_datetime = datetime.datetime.fromisoformat(match['fixture']['date']),
	# 			home_team_id = match['teams']['home']['id'],
	# 			away_team_id = match['teams']['away']['id'],
	# 			venue_id = match['fixture']['venue']['id'],
	# 			score = f"{match['goals']['home']}-{match['goals']['away']}",
	# 			status_short = match['fixture']['status']['short'],
	# 			status_long = match['fixture']['status']['long'],
	# 			league_round = match['league']['round']
	#
	# 			cur.execute("INSERT INTO matches "
	# 						"(match_id, contest_id, datetime, home_team_id, away_team_id, venue_id, score, status_short,"
	# 						"round, status_long)"
	# 						"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
	# 						(match_id, contest_id, match_datetime, home_team_id, away_team_id, venue_id, score,
	# 						 status_short, league_round, status_long))
	# 			conn.commit()


if __name__ == '__main__':
	db = Database()
	# db.delete_contest('Premier League', 'Russia', 2023)

