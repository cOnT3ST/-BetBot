import datetime
import logging
import telebot
from dotenv import load_dotenv
from bot_text_messages import *
import config
from typing import List, Tuple, Callable, Union
from stats_api import StatsAPIHandler
from database import Database
from utilities import initialize_logging, load_confidentials_from_env

initialize_logging()
# TODO use load_confidential_data.py
load_dotenv()
TELEGRAM_TOKEN: str = load_confidentials_from_env("TELEGRAM_TOKEN")
# TODO get rid of test account id and read it from db
ADMIN_ID = int(load_confidentials_from_env("ADMIN_ID"))
TEST_ACCOUNT_ID = int(load_confidentials_from_env("TEST_ACCOUNT_ID"))
COUNTRY: str = 'Russia'
LEAGUE: str = 'Premier League'


class EventBus:

    def __init__(self):
        self.callbacks = {}

    def register_callback(self, event_name, callback):
        if event_name not in self.callbacks:
            self.callbacks[event_name] = []
        self.callbacks[event_name].append(callback)

    def notify_callbacks(self, event_name, *args, **kwargs):
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                callback(*args, **kwargs)


class BetBot(telebot.TeleBot):
    # Commands available in bot menu:
    MENU_COMMANDS_TEXT: List[Tuple[str, str]] = [
        ('start', 'Запустить бота'),
        ('help', 'Перечень доступных команд'),
        ('admin', 'Функционал администратора')
    ]

    # Transforms MENU_COMMANDS_TEXT into a list of telebot command type
    MENU_TELEBOT_COMMANDS: List[telebot.types.BotCommand] = \
        [telebot.types.BotCommand(comm, desc) for comm, desc in MENU_COMMANDS_TEXT]

    # Admin only commands available after inputting 'admin' command:
    ADMIN_COMMANDS_TEXT: List[str] = [
        'Создать соревнование',
        'Команда 2',
        'Команда 3'
    ]

    def __init__(self, stats_api: StatsAPIHandler, database: Database, event_bus: EventBus):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
        self.api = stats_api
        self.db = database
        self.event_bus = event_bus

        self.set_my_commands(commands=BetBot.MENU_TELEBOT_COMMANDS)
        self.commands = self.get_available_commands()
        self.allowed_users_ids: List[int] = [ADMIN_ID]

        self.register_message_handler(self.handle_message)
        self.register_callback_query_handler(
            callback=self.handle_admin_callback,
            func=lambda query: 'admin' in query.data
        )

    def get_available_commands(self) -> List[str]:
        """Returns a list of / commands available for all users"""
        return [f'/{c.command}' for c in self.get_my_commands()]

    def notify_admin(self, text: str) -> None:
        """Sends message to admin only"""
        prefix = f"{datetime.datetime.now().strftime(config.PREFERRED_TIME_FORMAT)}\n"
        self.send_message(chat_id=ADMIN_ID, text=prefix + text, parse_mode='HTML')

    def start(self):
        self.notify_admin('<b>Бот запущен!</b>')
        self.polling(none_stop=True)

    @staticmethod
    def authorized_users(message_handler: Callable) -> Callable:
        """
        Decorator function that restricts access to all message handlers based on the user ID.

        Args:
            message_handler (Callable): The handler to be decorated.

        Returns:
            Callable: A decorated handler.

        """

        def wrapper(self, message):
            if message.from_user.id not in self.allowed_users_ids:
                self.delete_message(message.chat.id, message.id)
                self.send_message(message.chat.id, BOT_ACCESS_DENIED_MESSAGE)
            else:
                message_handler(self, message)

        return wrapper

    @authorized_users
    def handle_message(self, message: telebot.types.Message) -> None:
        keyboard = None
        if message.content_type not in ['text']:
            response_message = BOT_UNSUPPORTED_MESSAGE_TYPE_MESSAGE
        elif message.text.startswith('/'):
            response_message, keyboard = self.handle_command(message)
        else:
            response_message = 'Текстовые сообщения ботом не принимаются'
        self.send_message(message.from_user.id, response_message, reply_markup=keyboard)

    def handle_command(self, message: telebot.types.Message) \
            -> tuple[str, Union[telebot.types.InlineKeyboardMarkup, None]]:

        keyboard = None
        if message.text not in self.commands:
            response_message = BOT_UNSUPPORTED_COMMAND_MESSAGE
        elif message.text == '/start':
            response_message = BOT_START_MESSAGE
        elif message.text == '/help':
            commands_n_descriptions = ''.join([f'/{c.command} - {c.description}\n' for c in self.get_my_commands()])
            response_message = BOT_HELP_MESSAGE.format(commands_n_descriptions)
        elif message.text == '/admin':
            if message.from_user.id != ADMIN_ID:
                response_message = BOT_ADMIN_COMMANDS_DENIED_MESSAGE
            else:
                response_message = 'Выберите требуемую команду:'
                keyboard = self.create_admin_inline()
        else:
            response_message = BOT_COMMAND_NOT_SUPPORTED_MESSAGE
        return (response_message, keyboard)

    def handle_admin_callback(self, callback_query: telebot.types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        message_id = callback_query.message.id

        if callback_query.data == 'admin_button1':
            self._create_betting_contest()
        elif callback_query.data == 'admin_button2':
            self._feature_not_ready_yet()
        else:
            self._feature_not_ready_yet()

    def create_admin_inline(self) -> telebot.types.InlineKeyboardMarkup:
        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        for c in BetBot.ADMIN_COMMANDS_TEXT:
            button = telebot.types.InlineKeyboardButton(text=c, callback_data=f'admin_button{len(buttons) + 1}')
            buttons.append(button)
        inline_keyboard.add(*buttons)
        return inline_keyboard

    def _create_betting_contest(self) -> None:
        logging.info('A command to create a new betting contest received...')

        if self._current_football_season_already_in_db():
            return

        if not self._country_supported():
            return

        logging.info('Creating new betting contest...')
        self.notify_admin(BOT_CREATING_NEW_BETTING_CONTEST)

        current_football_season = self._create_current_football_season()
        if not current_football_season:
            return

        season_api_id = current_football_season['season_api_id']
        year = current_football_season['year']
        self._update_team_list(season_api_id, year)

        self._create_calendar(current_football_season)

        country = current_football_season['league_country']
        league = current_football_season['league_name']
        season = current_football_season['year']
        logging.info(f"Betting contest for {country} {league} season {season}-{season + 1} created.")
        self.notify_admin( BOT_NEW_BETTING_CONTEST_CREATED.format(country, league, season, season + 1))

    def _read_current_football_season(self) -> dict | None:
        contests = self.db.read_contests()
        for c in contests:
            if c['is_active'] == 1:
                return c
        return None

    def _current_football_season_already_in_db(self) -> bool:
        current_season = self._read_current_football_season()
        if current_season:
            league_country = current_season['league_country']
            league_name = current_season['league_name']
            year = current_season['year']
            logging.info(f"Failed to create contest. "
                         f"Season '{league_country}, {league_name}, {year}' already exists in db")
            self.notify_admin(
                BOT_FAILED_TO_CREATE_BETTING_CONTEST_SEASON_ALREADY_EXISTS.format(league_name, league_country, year)
            )
            return True
        return False

    def _country_supported(self) -> bool:
        if not self.api.country_supported(COUNTRY):
            logging.error(f"Failed to create contest. "
                          f"Could not find '{COUNTRY}' in the statistics service database. "
                          f"Country support may have ended.")
            self.notify_admin(BOT_FAILED_TO_CREATE_BETTING_CONTEST_COUNTRY_NOT_SUPPORTED.format(COUNTRY))
            return False
        return True

    def _create_current_football_season(self) -> None | dict[str, str | int]:
        current_season = self._download_current_football_season()
        if not current_season:
            return
        self._store_current_football_season_in_db(current_season)
        return current_season

    def _download_current_football_season(self) -> None | dict[str, str | int]:
        self.notify_admin(BOT_ATTEMPT_TO_DOWNLOAD_CURRENT_SEASON_INFO)
        league_country, league_name = COUNTRY, LEAGUE
        current_season = self.api.get_current_season(league_country, league_name)
        if not current_season:
            logging.error(f"Failed to create contest. "
                          f"Statistics service database hasn't updated current season '{league_name}, "
                          f"{league_country}' yet.")
            self.notify_admin(BOT_FAILED_TO_CREATE_CONTEST_NO_SEASON_INFO_YET.format(league_name, league_country))
            return
        self.notify_admin(BOT_CURRENT_SEASON_DATA_DOWNLOADED.format(league_name, league_country))
        logging.info(f"Current season '{league_name}, {league_country}' data obtained")
        return current_season

    def _store_current_football_season_in_db(self, current_season: dict[str, str | int]) -> None:
        self.notify_admin("Сохранение футбольного чемпионата в базе данных...")
        self.db.add_contest(current_season)
        self.notify_admin(BOT_CURRENT_FOOTBALL_SEASON_ADDED_TO_DB)

    def _update_team_list(self, season_api_id: int, year: int) -> None:
        self.notify_admin('Загружаем список команд чемпионата...')
        teams_list = self.api.get_league_teams(season_api_id, year)
        self.notify_admin('Команды загружены.')
        self.db.insert_missing_teams(teams_list)
        self.notify_admin('Обновляем команды в базе данных.')
        self.notify_admin(BOT_TEAM_LIST_UPDATED)

    def _create_calendar(self, current_season: dict[str, str | int]) -> None:
        self.notify_admin(BOT_CREATING_NEW_CALENDAR)
        logging.info('Downloading season calendar...')
        calendar = self._download_calendar(current_season)
        self._store_calendar_in_db(calendar)

    def _download_calendar(self, current_season: dict[str, str | int]) -> list[dict] | None:
        self.notify_admin('Загружаем календарь чемпионата...')
        full_calendar = self.api.get_calendar(current_season)
        if not full_calendar:
            logging.error(f"Failed to create contest. An error during calendar download")
            self.notify_admin(f"Не удалось создать соревнование. Возникла ошибка при загрузке календаря")
            return
        self.notify_admin(BOT_CALENDAR_DOWNLOADED)
        return full_calendar

    def _store_calendar_in_db(self, calendar: list[dict]) -> None:
        self.notify_admin('Сохраняем календарь в базе данных...')
        self.db.insert_matches(calendar)
        self.notify_admin(BOT_CALENDAR_ADDED_TO_DB)

    def on_requests_quota_reached(self, used_quota: int) -> None:
        """
        Handles events when the daily requests quota is reached or significant thresholds are met.

        Parameters:
        - used_quota (int): The percentage of the daily requests quota used.

        Returns:
        None

        This method checks if the provided `used_quota` falls within predefined significant thresholds.
        If the quota exceeds or matches any of these thresholds, it generates a warning message and sends it
        to the admin using the `notify_admin` method.

        Thresholds:
        - 30%, 50%, and 80%: Generate a warning about a significant requests quota reached.
        - 100%: Generate a warning about reaching the daily requests quota, indicating the reset time.

        Note: If the `used_quota` does not match any threshold, the method returns early without sending any message.
        """
        significant_quota_thresholds = (30, 50, 80, 100)
        warning_message = ''

        if used_quota not in significant_quota_thresholds:
            return
        elif used_quota in significant_quota_thresholds[:-1]:
            warning_message = BOT_SIGNIFICANT_REQUESTS_THRESHOLD_REACHED_MESSAGE.format(used_quota)
        elif used_quota == significant_quota_thresholds[-1]:
            warning_message = BOT_DAILY_REQUESTS_QUOTA_REACHED_MESSAGE.format(config.REQUESTS_COUNTER_RESET_TIME)
        self.notify_admin(warning_message)

    def _feature_not_ready_yet(self):
        self.notify_admin(BOT_COMMAND_NOT_SUPPORTED_MESSAGE)


if __name__ == "__main__":
    from pprint import pprint

    event_bus = EventBus()
    bot = BetBot(stats_api=StatsAPIHandler(), database=Database(), event_bus=EventBus())

    # bot._create_betting_contest()
    # bot.create_calendar(235, 2023)

    # scheduler.bot_scheduler.start()
    # scheduler.bot_scheduler.print_jobs()

    bot.start()
