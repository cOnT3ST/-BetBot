import sqlite3
import logging
from utilities import initialize_logging, load_confidentials_from_env
import team_parser
from typing import Literal
from config import DAILY_REQUESTS_QUOTA

# TODO hide db path into env
DB_PATH = 'db/TEST_MyRPLBetBot.db'
CREATE_DB_SQL_FILE_PATH = 'db/create_db_tables.sql'
initialize_logging()


class Database:
    def __init__(self):
        self.name = DB_PATH
        self.conn = None
        self.cur = None
        self._init_db()

    def __enter__(self):
        self.conn = sqlite3.connect(self.name)
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cur.close()
        if isinstance(exc_value, Exception):
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def _db_exists(self) -> bool:
        with self:
            self.cur.execute("SELECT name FROM sqlite_master WHERE type == 'table'")
            db_exists = bool(self.cur.fetchall())
            return db_exists

    def _init_db(self) -> None:
        try:
            if not self._db_exists():
                with open(CREATE_DB_SQL_FILE_PATH, 'r') as f:
                    sql_script = f.read()
                with self:
                    self.cur.executescript(sql_script)
                logging.info(f"SQL script executed successfully. "
                             f"'{self.name}' created!")

                self._populate_db()
                logging.info(f"'{self.name}' populated. Initial data stored.")
        except Exception as e:
            logging.exception(f"Error during database initialization: {e}")
            raise  # Re-raise the exception to see the traceback in the console

    def _populate_db(self) -> None:
        admin_user_data = {'telegram_id': load_confidentials_from_env('ADMIN_ID'), 'is_admin': 1}
        test_user_data = {'telegram_id': load_confidentials_from_env('TEST_ACCOUNT_ID')}
        users_to_insert = (admin_user_data, test_user_data)
        api_requests_data = {'requests_today': 0, 'daily_requests_quota': DAILY_REQUESTS_QUOTA}
        accurate_team_data_list = team_parser.main()

        for u in users_to_insert:
            self._insert_into_table('users', u)

        self._insert_into_table('api_requests', api_requests_data)

        for t in accurate_team_data_list:
            self._insert_into_table('accurate_team_data', t)

    def _read_table(self, table: str) -> tuple[dict]:
        with self:
            self.cur.execute(f"SELECT * FROM {table}")
            columns = tuple(i[0] for i in self.cur.description)
            rows = self.cur.fetchall()
            result = tuple({c: r for c, r in zip(columns, r)} for r in rows)
            return result

    def _table_exists(self, table_name: str) -> bool:
        with self:
            self.cur.execute("SELECT name FROM sqlite_master WHERE type == 'table'")
            db_table_names = tuple(i[0] for i in self.cur.fetchall())
            return table_name in db_table_names

    def _insert_into_table(self, table_name: str, data_to_insert: dict) -> None:
        with self:
            columns = ', '.join((data_to_insert.keys()))
            values = tuple(data_to_insert.values())
            question_marks = f"{', '.join('?' * len(values))}"
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({question_marks})"
            params = values

            data_to_log = data_to_insert
            if 'logo' in data_to_log: data_to_log['logo'] = 'BINARY DATA NOT LOGGED DUE TO SIZE'

            try:
                self.cur.execute(query, params)
                logging.info(f"Data inserted. "
                             f"Table: '{table_name}', data_to_insert: {data_to_log}.")
            except (sqlite3.DatabaseError, sqlite3.Error, OverflowError) as e:
                logging.error(f"Failed to insert data. "
                              f"Received: table_name: '{table_name}', data_to_insert: {data_to_log}. "
                              f"Error: {e.__repr__()}.")
                return

    def _update_table(self, table_name: str, data_to_update: dict) -> None:
        with self:
            query = f"UPDATE {table_name} " \
                    f"SET {', '.join([f'{k} = ?' for k in data_to_update.keys()])}"

            columns_to_update = tuple(data_to_update.keys())
            values_to_update = tuple(data_to_update.values())
            try:
                self.cur.execute(query, values_to_update)
                logging.info(f"Table updated. "
                             f"Table '{table_name}', columns: {columns_to_update}, new values: {values_to_update}'.")
            except (sqlite3.DatabaseError, sqlite3.Error, OverflowError) as e:
                logging.error(f"Failed to update table. "
                              f"Table: {table_name}, columns: {columns_to_update}, new values: {values_to_update}. "
                              f"Error: {e.__repr__()}.")
                return

    def _update_requests_counter(self, action: Literal['increment', 'reset']) -> None:
        """ Updates requests made today either by incrementing it by 1 either resetting it to zero. """
        requests_today_stored = self.read_requests_counter()
        requests_today_updated = requests_today_stored + 1 if action == 'increment' else 0
        self._update_table('api_requests', {'requests_today': requests_today_updated})

    def increment_requests_counter(self) -> None:
        """Increments the value of requests made today by one"""
        self._update_requests_counter('increment')

    def reset_requests_counter(self) -> None:
        """Sets requests made today to zero"""
        self._update_requests_counter('reset')
        logging.info(f"Daily requests quota reset.")

    def read_requests_counter(self) -> int:
        """ Gets a number of requests to the statistics data API made today. """
        return self._read_table('api_requests')[0]['requests_today']

    def read_contests(self):
        return self._read_table('contests')

    def add_contest(self, contest: dict) -> None:
        self._insert_into_table('contests', contest)

    def insert_missing_teams(self, team_list: list) -> None:
        # TODO add logging to success on inserting each team and overall 'Team list is up to date'
        for t in team_list:
            try:
                self._insert_into_table('teams', t)
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    continue
                else:
                    logging.error(f"Failed to insert team. "
                                  f"Error: {e.__repr__()}.")

    def insert_matches(self, matches_list: list[dict]) -> None:
        for m in matches_list:
            try:
                self._insert_into_table('matches', m)
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    continue
                else:
                    logging.error(f"Failed to insert team. "
                                  f"Error: {e.__repr__()}.")


if __name__ == '__main__':
    from pprint import pprint
    from stats_api import StatsAPIHandler

    db = Database()
    # teams_list = db._read_table('teams')
    # clean_teams_list = [{k: v for k, v in t.items() if k != 'logo'} for t in teams_list]
    # # print('------------------------------------------------------STATS API TEAM LIST')
    # # pprint(clean_teams_list)
    #
    # # print('')
    #
    # accurate_teams_list = db._read_table('accurate_team_data')
    # clean_accurate_teams_list = [{k: v for k, v in t.items() if k == 'name_eng'} for t in accurate_teams_list]
    # # print('------------------------------------------------------ACCURATE TEAM LIST')
    # # pprint(clean_accurate_teams_list)
    #
    # combined_list = {}
    #
    # for i, t in enumerate(teams_list):
    #     for j, a_t in enumerate(accurate_teams_list):
    #         if t['name'] == a_t['name_eng']:
    #             combined_list[i] = j
    #             break
    #
    # paired_teams = list(combined_list.keys())
    # paired_accurate_teams = list(combined_list.values())
    # print(f'COMBINED LIST: {combined_list}')
    # # print(f'PAIRED TEAMS: {paired_teams}')
    # # print(f'PAIRED ACCURATE TEAMS: {paired_accurate_teams}')
    # unpaired_teams = set(range(len(clean_teams_list))).difference(paired_teams)
    # unpaired_accurate_teams = set(range(len(clean_accurate_teams_list))).difference(paired_accurate_teams)
    # print(f'UNPAIRED TEAMS: {unpaired_teams}')
    # print(f'UNPAIRED ACCURATE TEAMS: {unpaired_accurate_teams}')
    #
    # for team_i in combined_list:
    #     accurate_team_i = combined_list[team_i]
    #     t = teams_list[team_i]
    #     a_t = accurate_teams_list[accurate_team_i]
    #     t['name'] = a_t['name']
    #     t['city'] = a_t['city']
    #
    # clean_teams_list = [{k: v for k, v in t.items() if k != 'logo'} for t in teams_list]
    # pprint(clean_teams_list)
