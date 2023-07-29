from telebot.custom_filters import SimpleCustomFilter
from database import User


class IsDeeplink(SimpleCustomFilter):
	key = 'is_deeplink'

	def check(self, message):
		text = message.text.split()
		return len(text) == 2


class IsAdmin(SimpleCustomFilter):
	key = 'is_admin'

	def check(self, message):
		user = User(message.from_user.id)
		return user.status in ['admin', 'moderator']