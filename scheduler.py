from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from dotenv import load_dotenv
from database import Database
from config import REQUESTS_COUNTER_RESET_TIME, SCHEDULER_TIMEZONE

DB_URL = 'db/MyRPLBetBot.db'

load_dotenv()

jobstores = {'default': SQLAlchemyJobStore(url=f'sqlite:///{DB_URL}', tablename='scheduled_jobs')}
executors = {'default': ThreadPoolExecutor(20)}
bot_scheduler = BackgroundScheduler(jobstores=jobstores,
                                    executors=executors,
                                    timezone=timezone(SCHEDULER_TIMEZONE)
                                    )


def test_print_job():
    print('SCHEDULED PRINT JOB IN PROGRESS ...')


def schedule_test_print_job():
    bot_scheduler.add_job(id='1',
                          func=test_print_job,
                          name='TEST PRINT JOB',
                          trigger=IntervalTrigger(seconds=2),
                          replace_existing=True
                          )


def schedule_reset_requests_counter(db_instance: Database):
    h, m, s = REQUESTS_COUNTER_RESET_TIME.split(':')
    bot_scheduler.add_job(id='2',
                          func=db_instance.reset_requests_counter,
                          name='RESET REQUESTS COUNTER',
                          trigger=CronTrigger(hour=h, minute=m, second=s),
                          replace_existing=True
                          )


def send_admin_message(text: str) -> None:
    from bet_bot import BetBot
    bot = BetBot()
    bot.notify_admin(text)


def schedule_bot_message_sending(message_text: str, trigger: IntervalTrigger | CronTrigger) -> None:
    bot_scheduler.add_job(id='3',
                          func=send_admin_message,
                          name='BOT ADMIN MESSAGE SENDING',
                          trigger=trigger,
                          replace_existing=True,
                          args=[message_text]
                          )


# if __name__ == '__main__':
#     db = Database()
#     schedule_test_print_job()
#
#     try:
#         bot_scheduler.start()
#         while True:
#             pass
#     except (KeyboardInterrupt, SystemExit):
#         bot_scheduler.shutdown()
