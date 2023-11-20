import datetime
import os
import telebot
from dotenv import load_dotenv
from config import BOT_START_MESSAGE, BOT_HELP_MESSAGE, BOT_ACCESS_DENIED_MESSAGE, BOT_UNSUPPORTED_COMMAND_MESSAGE, \
    BOT_ADMIN_COMMANDS_DENIED_MESSAGE, BOT_UNSUPPORTED_MESSAGE_TYPE_MESSAGE, BOT_COMMAND_NOT_SUPPORTED_MESSAGE, \
    DEFAULT_COUNTRY, DEFAULT_LEAGUE
from typing import List, Tuple, Optional, Callable, Union, Dict
from scheduler import Scheduler
from stats_api import StatsAPI
from database import Database
import threading



# TODO use load_confidential_data.py
load_dotenv()
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
# TODO get rid of test account id and read it from db
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TEST_ACCOUNT_ID = int(os.getenv("TEST_ACCOUNT_ID"))


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

    def __init__(self):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
        self.scheduler = Scheduler(bot=self)
        self.api = StatsAPI()
        self.db = Database()

        self.set_my_commands(commands=BetBot.MENU_TELEBOT_COMMANDS)
        self.commands = self.get_available_commands()
        self.allowed_users_ids: List[int] = [ADMIN_ID]

        self.register_message_handler(self.handle_message)
        self.register_callback_query_handler(
            callback=self.handle_admin_callback,
            func=lambda query: 'admin' in query.data
        )

        self.scheduler_thread = threading.Thread(target=self.scheduler.start)
        self.bot_thread = threading.Thread(target=self.start)
        self.scheduler_thread.start()
        self.bot_thread.start()

    def get_available_commands(self) -> List[str]:
        """Returns a list of / commands available for all users"""
        return [f'/{c.command}' for c in self.get_my_commands()]

    def send_admin_message(self, text: str) -> None:
        # Sends message to admin only
        self.send_message(chat_id=ADMIN_ID, text=text)

    def start(self):
        self.polling(none_stop=True, interval=0)

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

    def handle_command(
            self,
            message: telebot.types.Message
    ) -> tuple[str, Union[telebot.types.InlineKeyboardMarkup, None]]:

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
            self.create_contest()
        elif callback_query.data == 'admin_button2':
            self.send_message(chat_id, BOT_COMMAND_NOT_SUPPORTED_MESSAGE)
        else:
            self.send_message(chat_id, BOT_COMMAND_NOT_SUPPORTED_MESSAGE)

    def create_admin_inline(self) -> telebot.types.InlineKeyboardMarkup:
        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        for c in BetBot.ADMIN_COMMANDS_TEXT:
            button = telebot.types.InlineKeyboardButton(text=c, callback_data=f'admin_button{len(buttons) + 1}')
            buttons.append(button)
        inline_keyboard.add(*buttons)
        return inline_keyboard

    def create_contest(self) -> None:
        """Creates a betting contest for the current season"""

        if not self.api.country_supported(DEFAULT_COUNTRY):
            self.send_admin_message(
                f'Не удалось найти {DEFAULT_COUNTRY} в базе данных сервиса статистики.\n'
                f'Возможно, поддержка страны прекращена'
            )
            return

        current_season = self.api.determine_current_season()
        print("1")
        if not current_season:
            self.send_admin_message(f'Текущий сезон в сервисе статистики пока не стартовал.')
            return

        self.db.create_contests_table()
        if self.db.contest_exists(current_season['contest_api_id'], current_season['year']):
            self.send_admin_message(
                f"Такое соревнование сезона {current_season['year']}-{current_season['year'] + 1}"
                f" уже есть в базе данных"
            )
            return
        print("2")
        self.db.add_contest(**current_season)
        print("3")
        self.db.create_bets_table()
        print("4")
        self.create_calendar(current_season)
        self.send_admin_message(
            f"Соревнование по ставкам {current_season['league_country']} {current_season['league_name']}"
            f" сезона {current_season['year']}-{current_season['year'] + 1} создано!"
        )

    def create_calendar(self, season: Dict[str, Union[str, int]]):
        teams_list = self.api.get_all_teams(season['contest_api_id'], season['year'])
        self.send_admin_message("Список команд сезона успешно загружен с сайта статистики")
        self.db.create_teams_table()
        self.db.update_teams_list(teams_list)
        self.send_admin_message("Список команд сезона обновлен в базе данных")
        full_calendar = self.api.get_calendar(season)
        self.send_admin_message("Календарь успешно загружен с сайта статистики")
        self.db.create_matches_table()
        self.db.update_matches(full_calendar)
        self.send_admin_message("Календарь успешно добавлен в базу данных")


if __name__ == "__main__":
    bot = BetBot()

