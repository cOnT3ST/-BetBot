import os
import telebot
from dotenv import load_dotenv
import config
from typing import List, Tuple, Optional, Callable
from scheduler import Scheduler
import threading

load_dotenv()
TELEGRAM_TOKEN: str = os.getenv("TEST_TELEGRAM_TOKEN")
#TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
# TODO get rid of test account id and read it from db
TEST_ACCOUNT_ID = int(os.getenv("TEST_ACCOUNT_ID"))


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
        'Показать доступные турниры',
        'Команда 2',
        'Команда 3',
        'Команда 4',
        'Команда 5',
        'Команда 6',
        'Команда 7',
        'Команда 8',
        'Команда 9',
        'Команда 10',
    ]

    def __init__(self):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
        self.scheduler = Scheduler(bot=self)

        self.set_my_commands(commands=BetBot.MENU_COMMANDS)
        self.commands = self.get_available_commands()
        self.allowed_users: List[int] = [ADMIN_ID, TEST_ACCOUNT_ID]
        self.register_message_handler(self.handle_commands, commands=self.commands)
        self.register_message_handler(self.handle_messages)
        self.register_callback_query_handler(
            callback=self.handle_admin_callbacks,
            func=lambda query: 'admin' in query.data
        )

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
        elif message.text == '/admin':
            if message.from_user.id != ADMIN_ID:
                response_message = 'Этот функционал доступен только администратору бота'
            else:
                ik = self.create_admin_inline()
                self.send_message(message.from_user.id, 'Выберите требуемую команду:', reply_markup=ik)
                return
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

    def create_admin_inline(self) -> telebot.types.InlineKeyboardMarkup:
        inline_keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        buttons = []
        for c in BetBot.ADMIN_COMMANDS_TEXT:
            button = telebot.types.InlineKeyboardButton(text=c, callback_data=f'admin_button{len(buttons) + 1}')
            buttons.append(button)
        inline_keyboard.add(*buttons)
        return inline_keyboard

    def handle_admin_callbacks(self, callback_query: telebot.types.CallbackQuery) -> None:
        chat_id = callback_query.from_user.id
        message_id = callback_query.message.id

        if callback_query.data == 'admin_button1':
            self.send_message(chat_id, f'Здесь будет функционал кнопки {callback_query.data}')
        else:
            self.send_message(chat_id, 'Эта команда пока не поддерживается')

        self.edit_message_text(chat_id=chat_id, message_id=message_id, text=f'You pressed {callback_query.data}')



bot = BetBot()
