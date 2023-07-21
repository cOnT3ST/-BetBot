STAT_API_URL: str = 'https://rapidapi.com/api-sports/api/api-football'

SCHEDULER_TIMEZONE: str = 'Europe/Moscow'

DEFAULT_COUNTRY = 'Russia'
DEFAULT_TOURNAMENT = 'Premier League'

TEAMNAME_TRANSLATION = {
	"Arsenal Tula": "Арсенал", "CSKA Moskva": "ЦСКА", "Dinamo Moskva": "Динамо", "Dinamo St. Petersburg": "Сочи",
	"Khimki": "Химки", "Krasnodar": "Краснодар", "Krylya Sovetov": "Крылья Советов", "Lokomotiv Moskva": "Локомотив",
	"Nizhny Novgorod": "Нижний Новгород", "Rostov": "Ростов", "Rubin Kazan'": "Рубин", "Spartak Moskva": "Спартак",
	"Terek Grozny": "Терек", "Ufa": "Уфа", "Ural": "Урал", "Zenit": "Зенит"
}

PREFERRED_TIME_FORMAT = '%d.%m.%Y %H:%M'
MATCH_DURATION = 125  # Minutes after match starts
ROUND_DEADLINE = 30  # Minutes before all the bets are forbidden
MATCHDAY_STATUS_UPDATE_TIME = '07:00'  # At what time every day script sends an update request
# about today's match to statistics API


BOT_START_MESSAGE = "Всем привет! ✌\n" \
					"\n" \
					"Этот простой бот был создан с целью автоматизации нашего соревнования: " \
					"вместо того, чтобы пересылать друг другу фотографии предстоящих матчей," \
					"наших ставок, а также ведения вручную статистики в табличке экселя, я " \
					"постарался научить всему этому вот этого вот бота.\n" \
					"\n" \
					"Для доступа к имеющимся командам воспользуйтесь /help или кнопками, расположенными в меню\n" \
					"\n" \
					"❗ P.S. Бот находится на ранней стадии тестирования, поэтому в его работе" \
					" будет куча багов и ошибок. Просьба сообщать о них мне лично. Ну, и " \
					"фотографии с результатами пока тоже никто не отменял! 😉"
