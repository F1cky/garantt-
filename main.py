import telebot 
import random
import traceback
import threading
from telebot import types
from lib.db import *
from lib.moduls import *
from config import *
from sqlalchemy import and_, or_
from sqlalchemy import desc
from sqlalchemy_paginator import Paginator
from SimpleQIWI import *


db.metadata.create_all(engine)


bot = telebot.TeleBot(config['token'])

admin_id = int(config['admin_id'])
percent = int(config['percent'])
qiwi_phone = config['qiwi_phone']
qiwi_token = config['qiwi_token']

def user_button(user_id):
	button = types.ReplyKeyboardMarkup(True, False)
	button.row("✏️ Создать сделку", "🤝 Мои сделки")
	button.row("🎓 Мой профиль", "💬 Помощь")
	if user_id == admin_id:
		button.row('Админ')

	return button



def admin_button():
	button  = types.ReplyKeyboardMarkup(True, False)
	button.row("⁉️ Активные споры", "💰 Баланс")
	button.row("✉️ Рассылка", "📊 Статистика")
	button.row("Назад")
	return button


back_menu = types.ReplyKeyboardMarkup(True, True)
back_menu.row("Назад")


def del_inl(message, msg):
	if str(message.text) == "Назад":
		bot.delete_message(message.chat.id, msg.message_id)
		bot.send_message(message.chat.id, "Меню:", reply_markup = user_button(message.chat.id))


def create_deal(message, msg):
	try:
		username = str(message.text).replace('@', '').lower()
		if str(message.text) == "Назад":
			bot.delete_message(message.chat.id, msg.message_id)		
			bot.send_message(message.chat.id, "Меню:", reply_markup = user_button(message.chat.id))
			return

		elif username == str(message.chat.username).lower():
			bot.send_message(message.chat.id, 'Некорректное значение', reply_markup = user_button(message.chat.id))
			return

	##########################
		if check_is_username(username):
			session.rollback()
			user = session.query(User).filter_by(username = username).first()
			my = session.query(User).filter_by(user_id = message.chat.id).first()
			text = f"""
	🎓 Профиль: @{user.username}
	➖➖➖➖➖➖➖➖➖➖➖
	Сумма покупок: {user.buy_sum} ₽.
	Сумма продаж: {user.sale_sum} ₽.
	➖➖➖➖➖➖➖➖➖➖➖
	⚙️ Дата регистрации: {user.reg_date.strftime("%D")}
	"""
			deal_inl_btn = types.InlineKeyboardMarkup()
			buy = types.InlineKeyboardButton('✅ Я покупатель', callback_data = f'Dbuy:{my.user_id}:seller:{user.user_id}')
			seller = types.InlineKeyboardButton('✅ Я продавец', callback_data = f'Dbuy:{user.user_id}:seller:{my.user_id}')
			deal_inl_btn.add(buy, seller)
			msg = bot.send_message(message.chat.id, text, reply_markup = deal_inl_btn)
			bot.register_next_step_handler(msg, del_inl, msg)

		else:
			bot.send_message(message.chat.id, 'Пользоватль не разегистрированн в боте!', reply_markup = user_button(message.chat.id))
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))


def deal_price(message, buy_id, seller_id, deal_name):
	try:
		if '.' in message.text:
			price = float(message.text)
		else:
			i = message.text + '.0'
			price = float(i)

	except Exception as e:
		bot.send_message(message.chat.id, "<b>Некорректное значение!</b>", parse_mode = "HTML", reply_markup = user_button(message.chat.id))
		return
		
	unique_key = gen_unique_key()

	try:
		deal = Deal(deal_name = deal_name, buyer_id = int(buy_id), seller_id = int(seller_id), sum = price, unique_key = unique_key, percent = percent)
		session.add(deal)
		session.commit()
		session.rollback()
		d = session.query(Deal).filter_by(unique_key = unique_key).first()
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))

	if int(buy_id) == message.chat.id:
		sender_user_id = seller_id
	else:
		sender_user_id = buy_id

	text = f"""
<b>Предложение</b>
Название: {deal_name}
Сумма: {price} ₽
	"""
	send_button = types.InlineKeyboardMarkup()
	button = types.InlineKeyboardButton("Отправить предложение", callback_data = f"deal_id:{d.id}")
	send_button.add(button)
	bot.send_message(message.chat.id, text, reply_markup = send_button, parse_mode = "HTML") 


def deal_name(message, buy_id, seller_id):
	try:
		deal_name = str(message.text)
		msg = bot.send_message(message.chat.id, "Введите цену сделки:")
		bot.register_next_step_handler(msg, deal_price, buy_id, seller_id, deal_name)
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))

############################################################################################################################################
def active_deal(message, msg):
	chat_id = message.chat.id
	try:
		if message.text == "Назад":
			bot.send_message(message.chat.id, 'Меню:', reply_markup = user_button(message.chat.id))
			return

		try:
			deal_name, deal_id = str(message.text).split(' ')
			deal_id = int(deal_id.replace("(", '').replace(")", ''))
		except:
			bot.send_message(message.chat.id, 'Некорректное значение', reply_markup = user_button(message.chat.id))
			return

		session.rollback()
		deal = session.query(Deal).filter_by(id = deal_id).first()
		if deal == None:
			bot.send_message(message.chat.id, 'У вас нет активных сделок.', reply_markup = user_button(message.chat.id))
			return

		elif deal.deal_name != deal_name: 
			bot.send_message(message.chat.id, 'У вас нет активных сделок.', reply_markup = user_button(message.chat.id))
			return

		elif deal.status == False:
			bot.send_message(message.chat.id, 'У вас нет активных сделок.', reply_markup = user_button(message.chat.id))
			return		
		
		elif deal.seller_id != chat_id:
			if deal.buyer_id != chat_id:
				bot.send_message(message.chat.id, 'У вас нет активных сделок.', reply_markup = user_button(message.chat.id))
				return	
			
		session.rollback()
		text = f"""
	<b>№ сделки:</b> {deal.id} 
	<b>Название:</b> {deal.deal_name}
	<b>Сумма:</b> {deal.sum} ₽
	<b>Продавец:</b> @{session.query(User).filter_by(user_id = deal.seller_id).first().username}
	<b>Покупатель:</b> @{session.query(User).filter_by(user_id = deal.buyer_id).first().username}
		"""

		button_active_deal = types.InlineKeyboardMarkup()
		spor = types.InlineKeyboardButton("🆘 Открыть спор", callback_data = f'open_dispute:{deal.id}')
		if int(deal.seller_id) == message.chat.id:
			end_btn = types.InlineKeyboardButton("❌ Прервать сделки", callback_data = f'break_deal:{deal.id}')
		elif int(deal.buyer_id) == message.chat.id:
			end_btn = types.InlineKeyboardButton("✅ Завершить сделку", callback_data = f'end_deal:{deal.id}')

		back = types.InlineKeyboardButton("⬅️Назад", callback_data = 'back_active_deal')
		button_active_deal.add(spor)
		button_active_deal.add(end_btn)
		button_active_deal.add(back)

		bot.delete_message(message.chat.id, msg.message_id)
		bot.send_message(message.chat.id, text, reply_markup = button_active_deal, parse_mode = 'HTML')
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))

###################################################################################################################################################

def withdraw_balance_end(message, phone):
	try:
		if message.text == "Назад":
			bot.send_message(message.chat.id, 'Меню:', reply_markup = user_button(message.chat.id))
			return

		try:
			if '.' in message.text:
				cash = float(message.text)
			else:
				i = message.text + '.0'
				cash = float(i)

		except Exception as e:
			bot.send_message(message.chat.id, "<b>Некорректное значение!</b>", parse_mode = "HTML", reply_markup = user_button(message.chat.id))
			return

		session.rollback()
		user = session.query(User).filter_by(user_id = message.chat.id).first()

		if user.balance < cash:
			bot.send_message(chat_id, "Недостаточно средств!", reply_markup = user_button(message.chat.id))
			return

		user.balance -= cash
		session.add(user)
		session.commit()
		if transfer(phone, cash):
			bot.send_message(message.chat.id, "Деньги выведены!", reply_markup = user_button(message.chat.id))
			return

		bot.send_message(message.chat.id, "Ошибка во время транзакции, попробуйте чуть позже!", reply_markup = user_button(message.chat.id))
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))
		

def withdraw_balance(message):
	phone = message.text

	if phone == "Назад":
		bot.send_message(message.chat.id, 'Меню:', reply_markup = user_button(message.chat.id))
		return

	if len(phone) != 11:
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup = user_button(message.chat.id))
		return 

	try:
		int(phone)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup = user_button(message.chat.id))
		return

	if phone[0] != '7':
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup = user_button(message.chat.id))
		return		

	msg = bot.send_message(message.chat.id, "Введите сумму которую хотите вывести:", reply_markup = back_menu)
	bot.register_next_step_handler(msg, withdraw_balance_end, phone)



def withdraw_balance_end_admin(message, phone):
	try:
		if message.text == "Назад":
			bot.send_message(message.chat.id, 'Админ панель:', reply_markup = admin_button())
			return

		try:
			if '.' in message.text:
				cash = float(message.text)
			else:
				i = message.text + '.0'
				cash = float(i)

		except Exception as e:
			bot.send_message(message.chat.id, "<b>Некорректное значение!</b>", parse_mode = "HTML", reply_markup = admin_button())
			return

		session.rollback()
		my_balance = session.query(My_balance).first()

		if my_balance == None:
			bot.send_message(chat_id, "Недостаточно средств!", reply_markup = admin_button())
			return		

		if my_balance.cash < cash:
			bot.send_message(chat_id, "Недостаточно средств!", reply_markup = admin_button())
			return

		my_balance.cash -= cash
		session.add(my_balance)
		session.commit()
		if transfer(phone, cash):
			bot.send_message(message.chat.id, "Деньги выведены!", reply_markup = admin_button())
			return

		bot.send_message(message.chat.id, "Ошибка во время транзакции, попробуйте чуть позже!", reply_markup = admin_button())
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = admin_button())



def withdraw_balance_admin(message):
	phone = message.text

	if phone == "Назад":
		bot.send_message(message.chat.id, 'Админ панель:', reply_markup = admin_button())
		return

	if len(phone) != 11:
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup =  admin_button())
		return 

	try:
		int(phone)
	except Exception as e:
		print(e)
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup =  admin_button())
		return

	if phone[0] != '7':
		bot.send_message(message.chat.id, "Не корректный номер телефона!", reply_markup =  admin_button())
		return		

	msg = bot.send_message(message.chat.id, "Введите сумму которую хотите вывести:", reply_markup = back_menu)
	bot.register_next_step_handler(msg, withdraw_balance_end_admin, phone)


###################################################################################################################################################

def spam(text):
	try:
		good = 0
		error = 0
		users = session.query(User).all()
		for user in users:
			try:
				bot.send_message(user.user_id, text, parse_mode = 'HTML')
				good += 1
			except Exception as e:
				error += 1


		msg_text = f"""
<b>Рассылка завершена!</b>
Успешно: {str(good)}
Ошибок: {str(error)}
"""
		bot.send_message(admin_id, msg_text, parse_mode = 'HTML')
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(admin_id, "Что-то пошло не так!")		

def start_spam(message):
	try:
		text = message.text
		t = threading.Thread(target = spam, args = (text,))
		t.start()
	except Exception as e:
		error_log(traceback.format_exc())
		bot.send_message(admin_id, "Что-то пошло не так!")



@bot.message_handler(commands = ['start'])
def start(message):
	add_user(message.chat.id, message.chat.username)
	update_username(message.chat.id, message.chat.username)
	bot.send_message(message.chat.id, f"{message.chat.first_name} добро пожаловать в нашего гарант бота!", reply_markup = user_button(message.chat.id), parse_mode = 'HTML')


@bot.message_handler(content_types = ['text'])
def main(message):
	text = str(message.text)
	chat_id = message.chat.id
	message_id = message.message_id
	if message.text:
		add_user(message.chat.id, message.chat.username)
		update_username(message.chat.id, message.chat.username)

		
	if text == "Админ" and chat_id == admin_id:
		bot.send_message(chat_id, "Админ панель:", reply_markup = admin_button())


	elif text == '💰 Баланс' and chat_id == admin_id:
		session.rollback()
		balance = QApi(token=qiwi_token, phone=qiwi_phone).balance[0]
		my_balance_adm = session.query(My_balance).first()
		if my_balance_adm.cash == None:
			cash = 0.0
		else:
			cash = my_balance_adm.cash

		balance_btn = types.InlineKeyboardMarkup()
		btn = types.InlineKeyboardButton('💵 Вывести деньги', callback_data = "withdraw_balance_admin")
		balance_btn.row(btn)

		msg_text = f"""
<b>Общий баланс Qiwi кошелька:</b> {balance} ₽.
<b>Сумма дозволимая на вывод:</b> {cash} ₽.
"""
		bot.send_message(chat_id, msg_text, parse_mode = "HTML", reply_markup = balance_btn)

	elif text == '📊 Статистика' and chat_id == admin_id:
		try:
			all_users = session.query(User).count()
			bot.send_message(chat_id, f"На данный момент в боте {all_users} пользователей!")
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif text == '✉️ Рассылка' and chat_id == admin_id:
		msg = bot.send_message(chat_id, "Введите текст рассылки:")
		bot.register_next_step_handler(msg, start_spam)


	elif text == '⁉️ Активные споры' and chat_id == admin_id:
		try:
			session.rollback()
			dispute = session.query(Deal).filter_by(dispute = True).order_by(desc(Deal.id))
			if dispute.count() == 0:
				bot.send_message(chat_id = chat_id, text = "Активных споров нет!")
				return

			page_number = 1
			if page_number == 1:
				bot.delete_message(chat_id, message_id)


			paginators = Paginator(dispute, 5)
			page = paginators.page(page_number)

			views = types.InlineKeyboardMarkup()

			for disp in page.object_list:
				btn = types.InlineKeyboardButton(f"№{disp.id}|{disp.deal_name}", callback_data = f'disp_details:{disp.id}:page:{page_number}')
				views.row(btn)
			
			previous = types.InlineKeyboardButton("⏪", callback_data = f"views_dispute:{str(page_number-1)}")
			number = types.InlineKeyboardButton(str(page.number), callback_data = 'null')
			next = types.InlineKeyboardButton("⏩", callback_data =  f"views_dispute:{str(page_number+1)}")
			back = types.InlineKeyboardButton("Назад", callback_data = "admin_menu")

			if page.has_previous() and page.has_next():
				views.add(previous, number, next)
			elif page.has_next():
				views.add(number, next)
			elif page.has_previous():
				views.add(previous, number)
			views.row(back)

			bot.send_message(chat_id = message.chat.id, text = "Активные споры:", reply_markup = views)
		except Exception as e:
			print(e)
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif text == '💬 Помощь':
		support_url =  "https://t.me/" + config['support'].replace("@", '')
		support_btn = types.InlineKeyboardMarkup()
		support = types.InlineKeyboardButton("☎️ Поддержка", url = support_url)
		instruction = types.InlineKeyboardButton("📃 Инструкция", callback_data = 'instruction')
		support_btn.add(support, instruction)
		bot.send_message(chat_id, "Дополнительно: ", reply_markup = support_btn)

	elif text == "✏️ Создать сделку":
		msg = bot.send_message(message.chat.id, "Введите <i>@Username</i> пользователя:", parse_mode = 'HTML', reply_markup = back_menu)
		bot.register_next_step_handler(msg, create_deal, msg)


	elif text == "🤝 Мои сделки":
		try:
			session.rollback()
			deals = session.query(Deal).filter(and_(or_(Deal.buyer_id == chat_id, Deal.seller_id == chat_id), Deal.status == True))
			deals_button = types.ReplyKeyboardMarkup(resize_keyboard=True)
			for i in deals:
				deals_button.row(i.deal_name + f' ({str(i.id)})')
			deals_button.row("Назад")

			if deals.count() == 0:
				bot.send_message(chat_id, "У вас нет активных сделок.", reply_markup = user_button(chat_id))
				return

			msg = bot.send_message(message.chat.id, "Активные сделки: ", reply_markup = deals_button)
			bot.register_next_step_handler(msg, active_deal, msg)
		except Exception as e:
			print(e)
			bot.send_message(message.chat.id, "<b>Что-то пошло не так!</b>", parse_mode = "HTML", reply_markup = user_button(message.chat.id))
			return

	elif text == "🎓 Мой профиль":
		try:
			session.rollback()
			user = session.query(User).filter_by(user_id = message.chat.id).first()
			msg_text = f"""
	🎓 Профиль: @{user.username}
	🏷 Ваш баланс: {user.balance} ₽.
	➖➖➖➖➖➖➖➖➖➖➖
	Сумма покупок: {user.buy_sum} ₽.
	Сумма продаж: {user.sale_sum} ₽.
	➖➖➖➖➖➖➖➖➖➖➖
	⚙️ Дата регистрации: {user.reg_date.strftime("%D")}
			"""
			profile_button = types.InlineKeyboardMarkup()
			replenish_balance = types.InlineKeyboardButton("💳 Пополнить баланс", callback_data = 'replenish_balance')
			withdraw_balance = types.InlineKeyboardButton("💵 Вывести средства", callback_data = 'withdraw_balance_admin')
			profile_button.row(replenish_balance)
			profile_button.row(withdraw_balance)
			bot.send_message(message.chat.id, msg_text, reply_markup = profile_button)
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")

	elif text == "Назад":
		bot.send_message(message.chat.id, 'Меню:', reply_markup = user_button(message.chat.id))



@bot.callback_query_handler(func=lambda call: True)
def inline(call):
	chat_id = call.message.chat.id
	message_id = call.message.message_id


	if call.data[:13] == 'views_dispute':
		try:
			session.rollback()
			dispute = session.query(Deal).filter_by(dispute = True).order_by(desc(Deal.id))
			if dispute.count() == 0:
				bot.send_message(chat_id = chat_id, text = "Активных споров нет!")
				return

			page_number = int(call.data[14:])
			if page_number == 1:
				bot.delete_message(chat_id, message_id)


			paginators = Paginator(dispute, 5)
			page = paginators.page(page_number)

			views = types.InlineKeyboardMarkup()

			for disp in page.object_list:
				btn = types.InlineKeyboardButton(f"№{disp.id}|{disp.deal_name}", callback_data = f'disp_details:{disp.id}:page:{page_number}')
				views.row(btn)
			
			previous = types.InlineKeyboardButton("⏪", callback_data = f"views_dispute:{str(page_number-1)}")
			number = types.InlineKeyboardButton(str(page.number), callback_data = 'null')
			next = types.InlineKeyboardButton("⏩", callback_data =  f"views_dispute:{str(page_number+1)}")
			back = types.InlineKeyboardButton("Назад", callback_data = "admin_menu")

			if page.has_previous() and page.has_next():
				views.add(previous, number, next)
			elif page.has_next():
				views.add(number, next)
			elif page.has_previous():
				views.add(previous, number)
			views.row(back)

			if page_number == 1:
				bot.send_message(chat_id = call.message.chat.id, text = "Активные споры:", reply_markup = views)
			else:	
				bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id, text = "Активные споры:", reply_markup = views)
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif call.data[:12] == 'disp_details':
		null, deal_id, null, page_number = str(call.data).split(':')
		try:
			session.rollback()
			deal = session.query(Deal).filter_by(id = deal_id).first()

			text = f"""
	<b>№ сделки:</b> {deal.id} 
	<b>Название:</b> {deal.deal_name}
	<b>Сумма:</b> {deal.sum} ₽
	<b>Продавец:</b> @{session.query(User).filter_by(user_id = deal.seller_id).first().username}
	<b>Покупатель:</b> @{session.query(User).filter_by(user_id = deal.buyer_id).first().username}
			"""
			disp_button = types.InlineKeyboardMarkup()
			seller_btn = types.InlineKeyboardButton(text = "✅ В пользу продавца", callback_data = f'in_favor_seller:{deal_id}')
			buyer_btn = types.InlineKeyboardButton(text = "✅ В пользу покупателя", callback_data = f'in_favor_buyer:{deal_id}')
			back = types.InlineKeyboardButton(text = "Назад", callback_data = f'views_dispute:{page_number}')
			disp_button.add(seller_btn) 
			disp_button.add(buyer_btn) 
			disp_button.add(back)

			bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id, text = text, reply_markup = disp_button, parse_mode = 'HTML')

		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))
			return


	elif call.data == 'admin_menu':
		bot.delete_message(call.message.chat.id, call.message.message_id)
		bot.send_message(call.message.chat.id, 'Админ панель:', reply_markup = admin_button())


	elif call.data == 'replenish_balance':
		try:
			session.rollback()
			balance_btn = types.InlineKeyboardMarkup()
			btn = types.InlineKeyboardButton("💳 Проверить оплату", callback_data = 'check_pay')
			back = types.InlineKeyboardButton("⬅️ Назад", callback_data = 'profile')
			balance_btn.add(btn, back)
			qiwi_code = random.randint(111111111, 999999999)
			user = session.query(User).filter_by(user_id = chat_id).first()
			user.qiwi_code = qiwi_code
			session.add(user)
			session.commit()

			msg_text = f"""
➖➖➖➖➖➖➖➖➖➖➖➖➖
<b>Способ оплаты:</b> Qiwi
<b>Номер для перевода:</b> <pre>{qiwi_phone}</pre>
<b>Комментарий к оплате:</b> <pre>{qiwi_code}</pre>
➖➖➖➖➖➖➖➖➖➖➖➖➖
<b>Внимание! Очень важно чтобы вы переводили деньги с этим комментарием, иначе средства не будут зачислены.</b>
	"""
			bot.edit_message_text(chat_id = chat_id, message_id = message_id, text = msg_text, parse_mode = "HTML", reply_markup = balance_btn)
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif call.data == 'check_pay':
		try:
			session.rollback()
			user = session.query(User).filter_by(user_id = chat_id).first()
			code = user.qiwi_code
			check_pay = check_pay_qiwi(code)
			if check_pay:
				bot.delete_message(chat_id, message_id)
				user.balance += check_pay
				user.qiwi_code = 0
				session.add(user)
				session.commit()
				bot.send_message(chat_id, f"Баланс пополнен на {str(check_pay)} ₽")
				return
		
			bot.send_message(chat_id, "<b>Оплата ещё не поступила!</b>", parse_mode = "HTML")

		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "<b>Оплата ещё не поступила!</b>", parse_mode = "HTML")

	elif call.data == 'withdraw_balance':
		msg = bot.send_message(chat_id, "Введите номер QIWI кошелька (в формате 7ХХХХХХХХХХ):", reply_markup = back_menu)
		bot.register_next_step_handler(msg, withdraw_balance)


	elif call.data == 'withdraw_balance_admin':
		msg = bot.send_message(chat_id, "Введите номер QIWI кошелька (в формате 7ХХХХХХХХХХ):", reply_markup = back_menu)
		bot.register_next_step_handler(msg, withdraw_balance_admin)		


	elif call.data == 'profile':
		try:
			session.rollback()
			user = session.query(User).filter_by(user_id = chat_id).first()
			msg_text = f"""
	🎓 Профиль: @{user.username}
	🏷 Ваш баланс: {user.balance} ₽.
	➖➖➖➖➖➖➖➖➖➖➖
	Сумма покупок: {user.buy_sum} ₽.
	Сумма продаж: {user.sale_sum} ₽.
	➖➖➖➖➖➖➖➖➖➖➖
	⚙️ Дата регистрации: {user.reg_date.strftime("%D")}
			"""
			profile_button = types.InlineKeyboardMarkup(True)
			replenish_balance = types.InlineKeyboardButton("💳 Пополнить баланс", callback_data = 'replenish_balance')
			withdraw_balance = types.InlineKeyboardButton("💵 Вывести средства", callback_data = 'withdraw_balance')
			profile_button.add(replenish_balance, withdraw_balance)

			bot.edit_message_text(chat_id = chat_id, message_id = message_id, text = msg_text, parse_mode = "HTML", reply_markup = profile_button)		
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif call.data[0] == "D":
		null, buy_id, null2, seller_id = str(call.data).split(':')
		msg = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Введите название сделки:")
		bot.register_next_step_handler(msg, deal_name, buy_id, seller_id)


	elif str(call.data[:7]) == "deal_id":
		try:
			session.rollback()
			deal_id = call.data[8:]
			deal = session.query(Deal).filter_by(id = deal_id).first()

			if int(deal.buyer_id) == chat_id:
				send_chat_id = int(deal.seller_id)
			else:
				send_chat_id = int(deal.buyer_id)

			text = f"""
	<b>Сделка</b>
	Название: {deal.deal_name}
	Сумма: {deal.sum} ₽
			"""
			button = types.InlineKeyboardMarkup()
			btn1 = types.InlineKeyboardButton("✅ Принять", callback_data = f'accept:{deal.id}')
			btn2 = types.InlineKeyboardButton("❌ Отклонить", callback_data = f'reject:{deal.id}')
			button.add(btn1, btn2)

			bot.send_message(send_chat_id, text, reply_markup = button, parse_mode = 'HTML')
			bot.edit_message_text(chat_id = call.message.chat.id, message_id = call.message.message_id,  text = "Предложение отправлено!")
			bot.answer_callback_query(call.id, "Предложение отправлено!", show_alert = True)
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif str(call.data[:6]) == "accept": #Принять
		try:
			session.rollback()
			deal_id = int(call.data[7:])
			deal = session.query(Deal).filter_by(id = deal_id).first()
			text = f"""
	<b>Сделка</b>
	Название: {deal.deal_name}
	Сумма: {deal.sum} ₽
			"""

			button = types.InlineKeyboardMarkup()
			btn = types.InlineKeyboardButton('💰 Оплатить', callback_data = f'pay:{deal.id}')
			button.add(btn)
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			bot.send_message(chat_id=int(deal.buyer_id), text=text, parse_mode = 'HTML', reply_markup = button)
			bot.send_message(int(deal.seller_id), "Сделка принята.\nЖдём оплату от покупателя!", reply_markup = user_button(int(deal.seller_id)))
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif str(call.data[:6]) == "reject": #Отклонить
		try:
			session.rollback()
			deal_id = int(call.data[7:])
			deal = session.query(Deal).filter_by(id = deal_id).first()
			if deal.seller_id == chat_id:
				send_id = deal.buyer_id
			elif deal.buyer_id == chat_id:
				send_id = deal.seller_id

			user = session.query(User).filter_by(user_id = chat_id).first()
			bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Предложение отклонено.")
			bot.send_message(send_id, f"@{user.username} отклонил ваше предложение!")
			session.delete(deal)
			session.commit()
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif str(call.data[:3]) == "pay":
		try:
			session.rollback()
			deal_id = int(call.data[4:])
			deal = session.query(Deal).filter_by(id = deal_id).first()
			user = session.query(User).filter_by(user_id = chat_id).first()
			price = result_sum(deal.sum, deal.percent)
			percent = deal.sum - price
			user_cashe = float(user.balance)

			if user_cashe < price:
				bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Недостаточно средств на балансе!")
				bot.send_message(deal.seller_id, "Сделка не было оплачена!", reply_markup = user_button(deal.seller_id))
				bot.answer_callback_query(call.id, "Недостаточно средств на балансе!", show_alert = True)
				return

			add_reserve_balance(price)
			add_procent_balance(percent)
			deal.status = True
			user.balance -= deal.sum
			session.add(deal)
			session.add(user)
			session.commit()
			bot.send_message(deal.seller_id, f"@{user.username} оплатил сделку.\nМожите прислать ему товар!", reply_markup = user_button(chat_id))
			bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text = "Сделка активирована, завершить или оспорить сделку можно в разделе: «🤝 Мои сделки»")
			bot.send_message(call.message.chat.id, 'Меню:', reply_markup = user_button(chat_id))
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")


	elif str(call.data[:8]) == "end_deal":
		bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
		deal_id = str(call.data[9:])
		try:
			session.rollback()
			deal = session.query(Deal).filter_by(id = deal_id).first()
			seller = session.query(User).filter_by(user_id = deal.seller_id).first()
			buyer = session.query(User).filter_by(user_id = deal.buyer_id).first()

			cash = result_sum(deal.sum, deal.percent)
			procent_sum = float(deal.sum) - cash

			reserve_balance = session.query(Reserve_balance).first()
			reserve_balance.cash -= cash
			session.add(reserve_balance)

			procent_balance = session.query(Procent_balance).first()
			procent_balance.cash -= procent_sum
			session.add(procent_balance)
			
			seller.balance += cash
			seller.sale_sum += cash
			session.add(seller)

			buyer.buy_sum += cash
			session.add(buyer)
			add_my_balance(procent_sum)

			deal.end = True
			deal.status = False
			session.add(deal)

			session.commit()
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))
			return

		bot.send_message(chat_id, "Сделка завершена!", reply_markup = user_button(chat_id))
		bot.send_message(seller.user_id, f"Сделка №{str(deal.id)} завершена!\nНа ваш счёт зачисленно {str(cash)} ₽")
#################################################################################################################################

	elif str(call.data[:10]) == "break_deal":
		bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
		deal_id = int(call.data[11:])
		try:
			session.rollback()
			deal = session.query(Deal).filter_by(id = deal_id).first()
			seller = session.query(User).filter_by(user_id = deal.seller_id).first()
			buyer = session.query(User).filter_by(user_id = deal.buyer_id).first()

			cash = result_sum(deal.sum, deal.percent)
			procent_sum = float(deal.sum) - cash

			reserve_balance = session.query(Reserve_balance).first()
			reserve_balance.cash -= cash
			session.add(reserve_balance)

			procent_balance = session.query(Procent_balance).first()
			procent_balance.cash -= procent_sum
			session.add(procent_balance)

			buyer.balance += deal.sum
			session.add(buyer)

			session.delete(deal)
			session.commit()
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))
			return

		bot.send_message(chat_id, "Сделка прерванна!", reply_markup = user_button(chat_id))
		bot.send_message(buyer.user_id, f"@{seller.username} прервал сделку!")
	
	elif str(call.data[:12]) == "open_dispute":
		deal_id = int(call.data[13:])
		try:
			session.rollback()
			deal = session.query(Deal).filter_by(id = deal_id).first()
			user = session.query(User).filter_by(user_id = chat_id).first()
			if deal.dispute:
				bot.send_message(chat_id, "Спорт уже открыт, ждите ответа администратора!")
				return

			if deal.seller_id == chat_id:
				send_id = deal.buyer_id
			elif deal.buyer_id == chat_id:
				send_id = deal.seller_id

			deal.dispute = True
			session.add(deal)
			session.commit()
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))
			return

		text = f"""
<b>Открыт спор!</b>
<b>№ сделки:</b> {deal.id} 
<b>Название:</b> {deal.deal_name}
<b>Сумма:</b> {deal.sum} ₽
<b>Продавец:</b> @{session.query(User).filter_by(user_id = deal.seller_id).first().username}
<b>Покупатель:</b> @{session.query(User).filter_by(user_id = deal.buyer_id).first().username}
		"""
		disp_button = types.InlineKeyboardMarkup()
		seller_btn = types.InlineKeyboardButton(text = "✅ В пользу продавца", callback_data = f'in_favor_seller:{deal_id}')
		buyer_btn = types.InlineKeyboardButton(text = "✅ В пользу покупателя", callback_data = f'in_favor_buyer:{deal_id}')
		disp_button.add(seller_btn, buyer_btn)

		bot.delete_message(chat_id = call.message.chat.id, message_id=call.message.message_id)
		bot.send_message(chat_id = call.message.chat.id, text = "Спорт, отправлен на рассмотрение. Ждите ответа администратора!", reply_markup = user_button(chat_id))
		bot.send_message(send_id, f"@{user.username} открыл спор, ждите ответа администратора!")

		bot.send_message(admin_id, text, parse_mode = "HTML", reply_markup = disp_button)


	elif call.data == "back_active_deal":
		try:
			session.rollback()
			deals = session.query(Deal).filter(and_(or_(Deal.buyer_id == chat_id, Deal.seller_id == chat_id), Deal.status == True))
			deals_button = types.ReplyKeyboardMarkup(resize_keyboard=True)
			for i in deals:
				deals_button.row(i.deal_name + f' ({str(i.id)})')
			deals_button.row("Назад")

			if deals.count() == 0:
				bot.send_message(chat_id, "У вас нет активных сделок.", reply_markup = user_button(chat_id))
				return

			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			msg = bot.send_message(chat_id, "Активные сделки: ", reply_markup = deals_button)
			bot.register_next_step_handler(msg, active_deal, msg)
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!", reply_markup = user_button(chat_id))


	elif str(call.data[:15]) == 'in_favor_seller' and chat_id == admin_id:
		try:
			session.rollback()
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			deal_id = int(call.data[16:])
			deal = session.query(Deal).filter_by(id = deal_id).first()
			seller = session.query(User).filter_by(user_id = deal.seller_id).first()
			buyer = session.query(User).filter_by(user_id = deal.buyer_id).first()

			cash = result_sum(deal.sum, deal.percent)
			procent_sum = float(deal.sum) - cash

			reserve_balance = session.query(Reserve_balance).first()
			reserve_balance.cash -= cash
			session.add(reserve_balance)

			procent_balance = session.query(Procent_balance).first()
			procent_balance.cash -= procent_sum
			session.add(procent_balance)
			
			seller.balance += cash
			seller.sale_sum += cash
			session.add(seller)

			buyer.buy_sum += cash
			session.add(buyer)
			add_my_balance(procent_sum)

			deal.end = True
			deal.status = False
			session.add(deal)
			session.commit()

			bot.send_message(chat_id, 'Сделка завершена!')
			bot.send_message(buyer.user_id, f"Сделка завершена в пользу @{seller.username}")
			bot.send_message(seller.user_id, f"Сделка №{str(deal.id)} завершена в вашу пользу!\nНа ваш счёт зачисленно {str(cash)} ₽")
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")
			return		


	elif str(call.data[:14]) == 'in_favor_buyer' and chat_id == admin_id:
		try:
			session.rollback()
			bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
			deal_id = int(call.data[15:])
			deal = session.query(Deal).filter_by(id = deal_id).first()
			seller = session.query(User).filter_by(user_id = deal.seller_id).first()
			buyer = session.query(User).filter_by(user_id = deal.buyer_id).first()

			cash = result_sum(deal.sum, deal.percent)
			procent_sum = float(deal.sum) - cash

			reserve_balance = session.query(Reserve_balance).first()
			reserve_balance.cash -= cash
			session.add(reserve_balance)

			procent_balance = session.query(Procent_balance).first()
			procent_balance.cash -= procent_sum
			session.add(procent_balance)

			buyer.balance += deal.sum
			session.add(buyer)

			session.delete(deal)
			session.commit()
			bot.send_message(chat_id, 'Сделка завершена!')
			bot.send_message(seller.user_id, f"Сделка завершена в пользу @{buyer.username}")
			bot.send_message(buyer.user_id, f"Сделка №{str(deal.id)} завершена в вашу пользу!\nНа ваш счёт зачисленно {str(cash)} ₽")
		except Exception as e:
			error_log(traceback.format_exc())
			bot.send_message(chat_id, "Что-то пошло не так!")
			return

	elif call.data == 'instruction':
		f = open('files/instruction.txt', encoding = 'UTF-8')
		inst = f.read()
		f.close()
		bot.send_message(call.message.chat.id, inst, parse_mode = 'HTML')


bot.polling(none_stop = True)
