import random
import requests
import json
import traceback
import os
from lib.db import *
from datetime import datetime
from SimpleQIWI import *



qiwi_phone = config['qiwi_phone']
qiwi_token = config['qiwi_token']



def error_log(log):
	date = str(datetime.utcnow().strftime("%d/%m/%y %H:%M"))
	error = f"""\n
_______________________________________________________________________________________________________________________________________________
|{date}        |
|______________________|

{log}
_______________________________________________________________________________________________________________________________________________
\n
"""
	
	if os.path.exists('error_log/logs.txt') == False:
		f = open("error_log/logs.txt", 'w')
		f.close()

	f = open("error_log/logs.txt", 'a')
	f.write(error)
	f.close()




def update_username(user_id, username):
	try:
		user = session.query(User).filter_by(user_id = user_id).first()
		if str(user.username) != str(username).lower():
			user.username = str(username).lower()
			session.add(user)
			session.commit()
	except Exception as e:
		print(traceback.format_exc())
		
		

def add_user(user_id, username):
	try:
		check_user = session.query(User).filter_by(user_id = user_id).first()
		if check_user == None:
			user = User(user_id = user_id, username = str(username).lower())
			session.add(user)
			session.commit()
	except Exception as e:
		print(traceback.format_exc())


def check_is_username(username):
	try:
		username = str(username).lower()
		user = session.query(User).filter_by(username = username).first()
		if user:
			return True
		
		return False
	except Exception as e:
		print(e)
		return False


def gen_unique_key():
	res = ''
	for i in range(50):
		r = random.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
		res = res + r

	return res



def transfer(phone, cash):
	try:
		api = QApi(token=qiwi_token, phone=qiwi_phone)
		api.pay(account=phone, amount=int(cash), comment='Гарант бот')
		return True
	except Exception as e:
		error_log(traceback.format_exc())
		return False		




def add_procent_balance(cash):
	balance = session.query(Procent_balance).first()
	if balance:
		balance.cash += float(cash)
		session.add(balance)
		session.commit()
		return

	balance = Procent_balance(cash = float(cash))
	session.add(balance)
	session.commit()


def add_my_balance(cash):
	balance = session.query(My_balance).first()
	if balance:
		balance.cash += float(cash)
		session.add(balance)
		session.commit()
		return

	balance = My_balance(cash = float(cash))
	session.add(balance)
	session.commit()


def add_reserve_balance(cash):
	balance = session.query(Reserve_balance).first()
	if balance:
		balance.cash += float(cash)
		session.add(balance)
		session.commit()
		return

	balance = Reserve_balance(cash = float(cash))
	session.add(balance)
	session.commit()


def procent_balance():
	balance = session.query(Procent_balance).first()
	return  float(balance.cash)


def reserve_balance():
	balance = session.query(Reserve_balance).first()
	return float(balance.cash)


def my_balance():
	balance = session.query(My_balance).first()
	return float(balance.cash)


def result_sum(sum, procent):
	sum = float(sum)
	my_sum = sum / 100 * procent
	res = float(sum-my_sum)
	return res


def check_pay_qiwi(code):
	try:
		phone = qiwi_phone
		token = qiwi_token
		s = requests.Session()
		s.headers['authorization'] = 'Bearer ' + token  
		parameters = {'rows': '50'}
		h = s.get('https://edge.qiwi.com/payment-history/v1/persons/' + phone + '/payments', params = parameters)
		req = json.loads(h.text)
		for i in range(len(req['data'])):
			if req['data'][i]['comment'] == str(code) and req['data'][i]['sum']['currency'] == 643:
				cash = float(req['data'][i]['sum']['amount'])
				return cash

		return False

	except Exception as e:
		error_log(traceback.format_exc())
		return False
