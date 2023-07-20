import os
import telebot
from dotenv import load_dotenv
import config
from typing import List, Tuple
from scheduler import Scheduler

load_dotenv()
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID: str = os.getenv("ADMIN_ID")


# TODO all methods in this file must have type hints -> check for it

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
		'Some func №1'
		'Some func №2'
		'Some func №3'
	]

	def __init__(self):
		super().__init__(token=TELEGRAM_TOKEN, parse_mode=None)
		self.set_my_commands(commands=BetBot.MENU_COMMANDS)
		self.scheduler = Scheduler(bot=self)
		self.scheduler.start()

	def send_admin_message(self, text: str) -> None:
		self.send_message(chat_id=ADMIN_ID, text=text)


bot = BetBot()


@bot.message_handler(func=lambda msg: msg.text[1:] in [c.command for c in bot.get_my_commands()])
def handle_commands(message) -> None:
	if message.text == '/start':
		response_message = config.BOT_START_MESSAGE
	elif message.text == '/help':
		response_message = 'HELP COMMAND CALLED'
	else:
		response_message = 'THIS COMMAND IS NOT FUNCTIONAL YET'
	bot.send_admin_message(response_message)


@bot.message_handler(func=lambda msg: True)
def handle_messages(message) -> None:
	bot.send_admin_message(
		'Текстовые сообщения ботом не принимаются.\n'
		'Пожалуйста, воспользуйтесь командами из поддерживаемого списка.\n'
		'\n'
		'Для вывода списка нажмите /help'
	)


if __name__ == '__main__':
	bot.polling(none_stop=True, interval=0)
