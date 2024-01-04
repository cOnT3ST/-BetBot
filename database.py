import mysql.connector
from mysql.connector import errorcode
import logging
import config
from utilities import initialize_logging, load_confidentials_from_env
import datetime
from typing import Literal


DB_HOST = str(load_confidentials_from_env("MYSQL_DB_HOST"))
DB_LOGIN = str(load_confidentials_from_env("MYSQL_DB_USERNAME"))
DB_PASSWORD = str(load_confidentials_from_env("MYSQL_DB_PASSWORD"))
# todo input host name used by railway.app before deploying https://docs.railway.app/guides/mysql
DB_NAME = 'my_rpl_bet_bot_db'

initialize_logging()


class Database:
    def __init__(self):
        self.name = DB_NAME
        self.conn = None
        self.cur = None
        self._init_db()

    def __enter__(self):
        self.conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_LOGIN,
            password=DB_PASSWORD,
            database=self.name
        )
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        self.cur.close()
        if isinstance(exc_value, Exception):
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def _init_db(self):
        try:
            if not self._db_exists():
                self._create_db()
                self._create_tables()
                self._populate_db()
        except mysql.connector.Error as e:
            logging.exception(f"Error during database initialization: {e}")
            raise  # Re-raise the exception to see the traceback in the console

    def _db_exists(self) -> bool:
        self.conn = mysql.connector.connect(host=DB_HOST, user=DB_LOGIN, password=DB_PASSWORD)
        self.cur = self.conn.cursor()
        self.cur.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{DB_NAME}'")
        db_exists = bool(self.cur.fetchall())
        self.cur.close()
        self.conn.close()
        return db_exists

    def _create_db(self):
        try:
            self.conn = mysql.connector.connect(host=DB_HOST, user=DB_LOGIN, password=DB_PASSWORD)
            self.cur = self.conn.cursor()
            create_db_query = f"CREATE DATABASE IF NOT EXISTS {self.name} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
            use_db_query = f"USE {self.name};"
            for q in (create_db_query, use_db_query):
                self.cur.execute(q)
            self.conn.commit()
            self.cur.close()
            self.conn.close()
            logging.info(f"'{self.name}' created!")
        except mysql.connector.Error as e:
            logging.exception(f"Error during database creation: {e}")
            raise  # Re-raise the exception to see the traceback in the console

    def _create_tables(self):
        with self:
            self._execute_sql_script("db/create_db_tables_mysql.sql")
            logging.info(f"SQL script executed successfully. "
                         f"Tables created!")

    def _execute_sql_script(self, filepath: str) -> None:
        with open(filepath) as f:
            raw_text = f.read()
        sql_queries = raw_text.split(';')

        for q in sql_queries:
            if q.strip():
                self.cur.execute(q)

    def _populate_db(self) -> None:
        admin_user_data = {
            'telegram_id': load_confidentials_from_env('ADMIN_ID'),
            'is_admin': 1,
            'creation_datetime': datetime.datetime.now().strftime(config.PREFERRED_DATETIME_FORMAT)
        }
        test_user_data = {
            'telegram_id': load_confidentials_from_env('TEST_ACCOUNT_ID'),
            'creation_datetime': datetime.datetime.now().strftime(config.PREFERRED_DATETIME_FORMAT)
        }
        users_to_insert = (admin_user_data, test_user_data)
        api_requests_data = {'requests_today': 0, 'daily_requests_quota': config.DAILY_REQUESTS_QUOTA}
        # accurate_team_data_list = team_parser.main()

        for u in users_to_insert:
            self._insert_into_table('users', u)

        self._insert_into_table('api_requests', api_requests_data)

        # for t in accurate_team_data_list:
        #     self._insert_into_table('accurate_team_data', t)

        logging.info(f"'{self.name}' populated. Initial data stored.")

    def _insert_into_table(self, table_name: str, data_to_insert: dict) -> None:
        with self:
            columns = ', '.join((data_to_insert.keys()))
            values = tuple(data_to_insert.values())
            placeholders = f"{', '.join(('%s ' * len(values)).split(' ')[:-1])}"
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
            params = values

            data_to_log = data_to_insert
            if 'logo' in data_to_log: data_to_log['logo'] = 'BINARY DATA NOT LOGGED DUE TO SIZE'

            try:
                self.cur.execute(query, params)
                logging.info(f"Data inserted. "
                             f"Table: '{table_name}', data_to_insert: {data_to_log}.")
            except mysql.connector.Error as e:
                logging.error(f"Failed to insert data. "
                              f"Received: table_name: '{table_name}', data_to_insert: {data_to_log}. "
                              f"Error: {e.__repr__()}.")
                return

    def _read_table(self, table: str) -> tuple[dict]:
        with self:
            self.cur.execute(f"SELECT * FROM {table}")
            columns = tuple(i[0] for i in self.cur.description)
            rows = self.cur.fetchall()
            result = tuple({c: r for c, r in zip(columns, r)} for r in rows)
            return result

    def _update_table(self, table_name: str, data_to_update: dict) -> None:
        with self:
            query = f"UPDATE {table_name} " \
                    f"SET {', '.join([f'{k} = %s' for k in data_to_update.keys()])}"

            columns_to_update = tuple(data_to_update.keys())
            values_to_update = tuple(data_to_update.values())
            try:
                self.cur.execute(query, values_to_update)
                logging.info(f"Table updated. "
                             f"Table '{table_name}', columns: {columns_to_update}, new values: {values_to_update}'.")
            except mysql.connector.Error as e:
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
            except mysql.connector.IntegrityError as e:
                if e.errno == errorcode.ER_DUP_ENTRY: # duplicate key error (team already exists)
                    continue
                logging.error(f"Failed to insert team. "
                              f"Error: {e.__repr__()}.")

    def insert_matches(self, matches_list: list[dict]) -> None:
        for m in matches_list:
            try:
                self._insert_into_table('matches', m)
            except mysql.connector.IntegrityError as e:
                if e.errno == errorcode.ER_DUP_ENTRY:  # duplicate key error (match already exists)
                    continue
                else:
                    logging.error(f"Failed to insert team. "
                                  f"Error: {e.__repr__()}.")

if __name__ == '__main__':
    from pprint import pprint

    db = Database()
