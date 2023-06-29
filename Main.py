import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import configparser
from multiprocessing import *
import json
import datetime
import Receiver
import ExecChecker
import STG1
import Order
import pprint
from apscheduler.schedulers.background import BackgroundScheduler
import os

class Main(QMainWindow):
    def __init__(self,Qlist, managerList, account_data, stg_name):
        super().__init__()

        print('시작작')

        self.app_key = account_data[0]
        self.secret_key = account_data[1]
        self.acc_num = account_data[2]
        self.id = account_data[3]
        self.motoo = account_data[4]

        self.PriceQ = Qlist[0]
        self.OrderQ = Qlist[1]
        self.OrderCheckQ = Qlist[2]
        self.ExecQ = Qlist[3]
        self.WindowQ = Qlist[4]

        self.BuyList = managerList[0]
        self.PriceManger = managerList[1]
        self.OrderManager = managerList[2]
        self.ExecManager = managerList[3]
        self.PositionManager = managerList[4]
        self.BalanceManager = managerList[5]
        self.TradingManager = managerList[6]
        self.stg_name = strategy_name

        self.setWindowTitle('주식시스템')
        self.setGeometry(300, 300, 300, 300)

        btn1 = QPushButton('주문 매니저', self)
        btn2 = QPushButton('체결 매니저', self)
        btn3 = QPushButton('종료버튼', self)
        btn4 = QPushButton('포지션 매니저', self)
        btn5 = QPushButton('전량청산 버튼', self)
        btn6 = QPushButton('밸런스 매니저', self)
        btn7 = QPushButton('가격 매니저', self)
        btn8 = QPushButton('트레이딩 매니저', self)
        btn9 = QPushButton('테스트 매수', self)
        btn10 = QPushButton('포지션매니저 초기화', self)
        btn11 = QPushButton('테스트 매도', self)

        btn1.move(20, 20)
        btn2.move(20, 60)
        btn3.move(20, 100)
        btn4.move(160, 20)
        btn5.move(160, 60)
        btn6.move(160, 100)
        btn7.move(160, 140)
        btn8.move(20, 140)
        btn9.move(20, 180)
        btn10.move(160, 180)
        btn11.move(20,220)

        btn1.clicked.connect(self.btn1)
        btn2.clicked.connect(self.btn2)
        btn4.clicked.connect(self.btn4)
        btn5.clicked.connect(self.btn5)
        btn6.clicked.connect(self.btn6)
        btn7.clicked.connect(self.btn7)
        btn3.clicked.connect(QCoreApplication.instance().quit)
        btn8.clicked.connect(self.btn8)
        btn9.clicked.connect(self.btn9)
        btn10.clicked.connect(self.btn10)
        btn11.clicked.connect(self.btn11)

    def btn1(self):
        pprint.pprint(dict(self.OrderManager))

    def btn2(self):
        pprint.pprint(dict(self.ExecManager))

    def btn4(self):
        print('포지션매니저입니다')
        pprint.pprint(dict(self.PositionManager))

    def btn5(self):
        print('전량청산시작')
        for stockCode in self.PositionManager.keys():
            buyQty = self.PositionManager[stockCode]['보유수량']
            if buyQty > 0:
                self.order.CreateMarketOrder('매도', stockCode, buyQty, '슈퍼ETF')

    def btn6(self):
        pprint.pprint(dict(self.BalanceManager))

    def btn7(self):
        pprint.pprint(dict(self.PriceManger))

    def btn8(self):
        pprint.pprint(dict(self.TradingManager))
        print('보유종목 리스트 >> ', self.BuyList)

    def btn9(self):
        print('테스트매수')
        try:
            self.OrderQ.put(('305540', '매수', 'market', 0, 10, '테스트'))
            TradingManager_update = self.TradingManager['305540']
            TradingManager_update['매수주문여부'] = True
            TradingManager_update['매수주문시간'] = datetime.datetime.now()
            self.TradingManager.update({'305540': TradingManager_update})
        except Exception as e:
            print(e)

    def btn11(self):
        print('테스트매도')
        try:
            self.OrderQ.put(('305540', '매도', 'market', 0, 10, '테스트'))
            TradingManager_update = self.TradingManager['305540']
            TradingManager_update['매도주문여부'] = True
            TradingManager_update['매도주문시간'] = datetime.datetime.now()
            self.TradingManager.update({'305540': TradingManager_update})
        except Exception as e:
            print(e)

    def btn10(self):
        os.remove(f'log/{self.stg_name}_보유현황.json', )
        for stockCode in self.PositionManager.keys():
            PositionManager_update = self.PositionManager[stockCode]
            for i, v in PositionManager_update.items():
                PositionManager_update[i] = 0
            self.PositionManager.update({stockCode : PositionManager_update})

            if stockCode in self.BuyList:
                self.BuyList.remove(stockCode)

        print('포지션매니저 초기화 완료')

def get_key(motoo: bool):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    if motoo == True: a = '모투'
    else: a = '실투'
    app_key = config[a]['app_key']
    secret_key = config[a]['secret_key']
    acc_num = config[a]['acc_num']
    id = config[a]['id']
    return app_key, secret_key, acc_num, id

def QuitAPP(app):
    app.quit()

if __name__ == '__main__':

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    witID = '27dd3db59261495e83ec262a33e13850'
    motoo = True
    app_key, secret_key, acc_num, id = get_key(motoo)
    account_data = [app_key, secret_key, acc_num, id, motoo]
    strategy_name = '에러봇'

    app = QApplication(sys.argv)
    window = Main(qlist, managerlist, account_data, strategy_name)
    window.show()

    pcs2 = Process(target = Order.Order, args = (qlist, managerlist, account_data, strategy_name), daemon = True).start()
    pcs1 = Process(target = ExecChecker.Checker, args=(qlist, managerlist, account_data, strategy_name),daemon=True).start()
    pcs3 = Process(target = Receiver.PriceReceiver, args = (witID, qlist, managerlist, account_data, strategy_name), daemon = True).start()
    pcs4 = Process(target = STG1.Strategy, args=(qlist, managerlist, account_data, strategy_name),daemon=True).start()

    schedular = BackgroundScheduler(timezone='Asia/Seoul', job_defaults={'max_instances': 10})
    schedular.start()
    schedular.add_job(QuitAPP, args = (app, ), trigger='cron', hour = '15', minute = '32')

    app.exec_()

