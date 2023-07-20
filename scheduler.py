from time import sleep
import schedule
from datetime import datetime, time


class Scheduler:

	def __init__(self):
		pass

	def _print_message_once(self, text):
		print(f'{datetime.now().strftime("%H:%M:%S")}: {text}')
		return schedule.CancelJob

	def schedule_message(self, text: str, hour: int, minute: int, second: int):
		time_obj = time(hour, minute, second)
		schedule.every().day.at(time_obj.strftime("%H:%M:%S")).do(self._print_message_once, text=text)

	def start(self):
		while True:
			schedule.run_pending()
			sleep(1)


s = Scheduler()

dt1 = (21, 54, 7)
dt2 = (21, 54, 22)
dt3 = (21, 54, 50)

for dt in (dt1, dt2, dt3):
	hour, minute, second = dt
	s.schedule_message(
		text="working ...",
		hour=hour,
		minute=minute,
		second=second
	)
print(schedule.jobs)

s.start()
