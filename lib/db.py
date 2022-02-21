from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import *

db = declarative_base()


engine = create_engine(f"mysql+pymysql://{config['mysql']['login']}:{config['mysql']['password']}@{config['mysql']['host']}/{config['mysql']['db_name']}?charset=utf8mb4")


session = Session(bind = engine)


class User(db):
	__tablename__ = 'user'
	id = Column(Integer, primary_key = True)
	user_id = Column(Integer)
	username = Column(String(120))
	balance = Column(Float, default = 0.0)
	sale_sum = Column(Float, default = 0.0)
	buy_sum = Column(Float, default = 0.0)
	qiwi_code = Column(Integer, default = 0)
	reg_date = Column(DateTime, default = datetime.utcnow)

	def __repr__(self):
		return f"<Username: {self.username}>"


class Deal(db):
	__tablename__ = 'deal'
	id = Column(Integer, primary_key = True)
	deal_name = Column(String(250))
	buyer_id = Column(Integer)
	seller_id = Column(Integer)
	sum = Column(Float)
	unique_key = Column(String(255))
	percent = Column(Float)
	status = Column(Boolean, default = False)
	dispute = Column(Boolean, default = False)
	end = Column(Boolean, default = False)

	def __repr__(self):
		return str(id)


class Procent_balance(db):
	__tablename__ = 'procent_balance'
	id = Column(Integer, primary_key = True)
	cash = Column(Float)

class My_balance(db):
	__tablename__ = 'my_balance'
	id = Column(Integer, primary_key = True)
	cash = Column(Float)

class Reserve_balance(db):
	__tablename__ = 'reserve_balance'
	id = Column(Integer, primary_key = True)
	cash = Column(Float)


