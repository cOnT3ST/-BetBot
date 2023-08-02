import os
import telebot
from dotenv import load_dotenv
from config import BOT_START_MESSAGE, BOT_HELP_MESSAGE
from typing import List, Tuple, Optional, Callable
from scheduler import Scheduler
import threading

load_dotenv()
TELEGRAM_TOKEN: str = os.getenv("TEST_TELEGRAM_TOKEN")
#TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
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
        #self.scheduler = Scheduler(bot=self)

        self.set_my_commands(commands=BetBot.MENU_COMMANDS)
        self.commands = self.get_available_commands()
        self.allowed_users: List[int] = [int(ADMIN_ID)]
        #self.register_message_handler(self.handle_command, commands=self.commands)
        self.register_message_handler(self.handle_message)

        #self.scheduler_thread = threading.Thread(target=self.scheduler.start)
        self.thread = threading.Thread(target=self.start)
        #self.scheduler_thread.start()
        self.thread.start()

    def get_available_commands(self) -> List[str]:
        return [f'/{c.command}' for c in self.get_my_commands()]

    def send_admin_message(self, text: str) -> None:
        #telebot.TeleBot.send_message(chat_id=ADMIN_ID)
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
                self.delete_message(message.chat.id, message.id)
                self.send_message(message.chat.id, "Доступ запрещен.\n\nВы не являетесь участником соревнования.")
            else:
                message_handler(self, message)

        return wrapper

    @authorized_users
    def handle_message(self, message: telebot.types.Message) -> None:
        if message.content_type not in ['text']:
            response_message = 'Этот бот принимает не принимает сообщения такого типа.'
        elif message.text.startswith('/'):
            response_message = self.handle_command(message)
        else:
            response_message = 'Текстовые сообщения ботом не принимаются'
        self.send_message(message.from_user.id, response_message)

    def handle_command(self, message: telebot.types.Message) -> str:
        if message.text not in self.commands:
            response_message = 'Похоже, вы ввели неподдерживаемую команду.' \
                               '\n\n' \
                               'Пожалуйста, воспользуйтесь командами из поддерживаемого списка.' \
                               '\n' \
                               'Для вывода списка нажмите /help"'
        elif message.text == '/start':
            response_message = BOT_START_MESSAGE
        elif message.text == '/help':
            commands_n_descriptions = ''.join([f'/{c.command} - {c.description}\n' for c in self.get_my_commands()])
            response_message = BOT_HELP_MESSAGE.format(commands_n_descriptions)
        else:
            response_message = 'Эта команда пока не поддерживается'
        return response_message
    

if __name__ == "__main__":
    bot = BetBot()
