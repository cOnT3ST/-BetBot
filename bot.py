import os
import telebot
from dotenv import load_dotenv
import config
from typing import List, Tuple, Optional, Callable
from scheduler import Scheduler
import threading

load_dotenv()
# TELEGRAM_TOKEN: str = os.getenv("TEST_TELEGRAM_TOKEN")
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID: str = os.getenv("ADMIN_ID")


class BetBot(telebot.TeleBot):
    # Commands available in bot menu:
    MENU_COMMANDS_TEXT: List[Tuple[str, str]] = [
        ('start', 'Запустить бота'),
        ('help', 'Перечень доступных команд'),
        ('admin', 'Функционал администратора')
    ]

    MENU_COMMANDS: List[telebot.types.BotCommand] = \
        [telebot.types.BotCommand(comm, desc) for comm, desc in MENU_COMMANDS_TEXT]

    # Admin only commands available after inputting 'admin' command:
    ADMIN_COMMANDS_TEXT: List[str] = [
        'Команда 1',
        'Команда 2',
        'Команда 3',
    ]

    def __init__(self):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
        self.scheduler = Scheduler(bot=self)

        self.set_my_commands(commands=BetBot.MENU_COMMANDS)
        self.commands = self.get_available_commands()
        self.allowed_users: List[int] = [int(ADMIN_ID)]
        self.register_message_handler(self.handle_commands, commands=self.commands)
        self.register_message_handler(self.handle_messages)

        self.scheduler_thread = threading.Thread(target=self.scheduler.start)
        self.thread = threading.Thread(target=self.start)
        self.scheduler_thread.start()
        self.thread.start()

    def get_available_commands(self) -> List[str]:
        return [c.command for c in self.get_my_commands()]

    def send_admin_message(self, text: str) -> None:
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
            if message.from_user.id not in self.allowed_users:
                self.send_message(message.chat.id, "Доступ запрещен.\n\nВы не являетесь участником соревнования.")
            else:
                message_handler(self, message)

        return wrapper

    @authorized_users
    def handle_commands(self, message: telebot.types.Message) -> None:
        if message.text == '/start':
            response_message = config.BOT_START_MESSAGE
        elif message.text == '/help':
            response_message = 'Это бот используется для автоматизации нашего соревнования ' \
                               'по ставкам.\n\nКоманды в чат можно писать самому при помощи слэша' \
                               ' (например /help), либо выбирать из меню, либо кликать по уже' \
                               ' указанным в чате.\n\nДоступные команды:\n'
            for c in self.get_my_commands():
                response_message += f'/{c.command} - {c.description}\n'
            response_message += '\nПо всем вопросам - пишите или звоните\nСпасибо за использование!'
        else:
            response_message = 'Эта команда пока не поддерживается'
        self.send_message(message.from_user.id, response_message)

    @authorized_users
    def handle_messages(self, message: telebot.types.Message) -> None:
        if message.content_type not in ['text']:
            response_message = 'Этот бот принимает не принимает сообщения такого типа.'
        elif message.text.startswith('/'):
            response_message = 'Похоже, вы ввели неподдерживаемую команду.'
        else:
            response_message = 'Текстовые сообщения ботом не принимаются'
        response_ending = "\n\n" \
                          "Пожалуйста, воспользуйтесь командами из поддерживаемого списка.\n" \
                          "Для вывода списка нажмите /help"
        self.send_message(message.from_user.id, response_message + response_ending)


bot = BetBot()
