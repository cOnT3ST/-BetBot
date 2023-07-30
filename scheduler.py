from time import sleep
import schedule
from datetime import datetime, time
from pytz import timezone
from config import SCHEDULER_RUN_TIMES
from dotenv import load_dotenv
import os

load_dotenv()
SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE")


class Scheduler:

    def __init__(self, bot):
        self.bot = bot
        self.timezone = timezone(SCHEDULER_TIMEZONE)
        self._schedule_test_messaging()

    def _job(self, text: str) -> None:
        msg = f'{datetime.now(tz=self.timezone).strftime("%H:%M:%S")}\nScheduled message:\n{text}'
        self.bot.send_admin_message(text=msg)
    # return schedule.CancelJob

    def _schedule_message_daily(self, text: str, run_time: str) -> None:
        time_obj = time.fromisoformat(run_time)
        schedule.every().day.at(time_obj.strftime("%H:%M:%S"), tz=self.timezone).do(self._job, text=text)

    def _schedule_test_messaging(self) -> None:
        t1, t2, t3 = SCHEDULER_RUN_TIMES
        self._schedule_message_daily(text='Доброе утро! Бот на связи', run_time=t1)
        self._schedule_message_daily(text='Обед! Bon appetit!', run_time=t2)
        self._schedule_message_daily(text='Рабочий день закончен. Хорошего вечера!', run_time=t3)

    def start(self):
        while True:
            schedule.run_pending()
            sleep(1)
