from time import sleep
import schedule
from datetime import datetime, time
from typing import Tuple
from pytz import timezone
from config import SCHEDULER_TIMEZONE, SCHEDULER_RUN_TIMES


class Scheduler:

	def __init__(self, bot):
		self.bot = bot
		self.timezone = timezone(SCHEDULER_TIMEZONE)
		self._schedule_test_messaging()


	def _job(self, text: str) -> None:
		msg1 = f'{datetime.now().strftime("%H:%M:%S")}\n'
		msg2 = 'Scheduled message:\n'
		msg3 = f'{text}'
		self.bot.send_admin_message(text=''.join([msg1, msg2, msg3]))

	# return schedule.CancelJob

	def _schedule_message_daily(self, text: str, hour: int, minute: int, second: int) -> None:
		time_obj = time(hour, minute, second)
		schedule.every().day.at(time_obj.strftime("%H:%M:%S"), tz=self.timezone).\
			do(self._job, text=text)

	def _schedule_test_messaging(self) -> None:
		t1, t2, t3 = SCHEDULER_RUN_TIMES
		self._schedule_message_daily(text='Доброе утро! Бот на связи', hour=t1[0], minute=t1[1], second=t1[2])
		self._schedule_message_daily(text='Обед! Bon appetit!', hour=t2[0], minute=t2[1], second=t2[2])
		self._schedule_message_daily(text='Рабочий день закончен. Хорошего вечера!', hour=t3[0], minute=t3[1], second=t3[2])

	def start(self):
		while True:
			schedule.run_pending()
			sleep(1)
