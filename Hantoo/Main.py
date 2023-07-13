import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import configparser
from multiprocessing import *
import pprint
from apscheduler.schedulers.background import BackgroundScheduler
import os
import Token
import quantbox
from pykrx import stock
import pandas as pd
import datetime

import Receiver
import ExecChecker
import STG1
import Order
import json


class Main(QMainWindow):
    def __init__(self, stg_option, Qlist, managerList, account_data):
        super().__init__()

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

        self.stg_name = stg_option['전략명']

        self.setWindowTitle(self.stg_name)
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
                self.order.CreateMarketOrder('매도', stockCode, buyQty, f'{self.stg_name}')

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
            self.OrderQ.put(('122630', '매수', 'market', 0, 10, '테스트'))
            TradingManager_update = self.TradingManager['305540']
            TradingManager_update['매수주문여부'] = True
            TradingManager_update['매수주문시간'] = datetime.datetime.now()
            self.TradingManager.update({'305540': TradingManager_update})
        except Exception as e:
            print(e)

    def btn11(self):
        print('테스트매도')
        try:
            self.OrderQ.put(('122630', '매도', 'market', 0, 10, '테스트'))
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

def getData(frdate, todate, witID, universe = []):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    id = config['퀀트박스']['ID']
    pw = config['퀀트박스']['PW']
    quantbox.set_credentials(id, pw)
    data = quantbox.get_wit(witID, from_date=frdate, to_date=todate, stock_codes=universe)['result'][witID]
    bsDate = stock.get_previous_business_days(fromdate=data.index[0], todate=data.index[-1])
    data.index = pd.to_datetime(data.index)

    return data.loc[bsDate]

def CreateUniverse(frdate, todate, witID, universe):
    cond_df = getData(frdate, todate, witID, universe)
    universe = cond_df[cond_df == True].iloc[-1].dropna()
    return list(universe.keys())

def GetHoldingList(stg_name):
    try:
        with open(f'{stg_name}_보유현황.json' ,'r') as file:
            position = json.load(file)
        position = eval(position)
        codeList = position.keys()
        buyList = []
        for code in codeList:
            entryQty = position[code]['보유수량']
            if entryQty > 0:
                buyList.append(code)
        return buyList
    except FileNotFoundError:
        print('매매내역 없음')
        return []

if __name__ == '__main__':

    motoo = True
    Token.Token(motoo).get_access_token()  # 토큰부터 업데이트,

    buyCond_id = 'c94aab2a2abc4f889d4eeba5af6cfcc9'
    sellCond_id = '950dd29001c2447e836fe24e86789c9d'

    frdate = '20230701'
    todate = '20230731'

    stg_name = '에러봇'  # 전략이름
    totalBetSize = 100  # 총자산대비 투자비중
    maxCnt = 10  # 최대 보유종목수
    buyOption = 'atmarket'  # 매수옵션
    sellOption = 'atmarket'  # 매도옵션
    target = 10  # 목표가
    loss = 10  # 손절가
    rebal = 10  # 리밸런싱 기간
    fee = 0.26  # 수수료

    stg_option = dict(전략명=stg_name, 총자산대비투자비중=totalBetSize, 최대보유종목수=maxCnt, 리밸런싱=rebal, 수수료=fee, 매수옵션=buyOption,
                      매도옵션=sellOption, 목표가=target, 손절가=loss)
    print('===== 투자전략 분석중 =====')
    subStocks = ['122630','305540']
    # buyList = GetHoldingList(stg_name)
    # if len(buyList) == 0:
    #     subStocks = CreateUniverse(frdate, todate, buyCond_id, universe=[])
    # else:
    #     subStocks = buyList
    #### 보유종목이 있으면 그 종목들을 구독함
    #### 보유종목이 없으면 윗 아이디로 매수조건을 충족하는 종목들을 구독함

    print('===== 투자전략 분석 완료 =====')

    print(f'구독 종목 리스트 >> {subStocks}')

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    app_key, secret_key, acc_num, id = get_key(motoo)
    account_data = [app_key, secret_key, acc_num, id, motoo]

    app = QApplication(sys.argv)
    a = Main(stg_option, qlist, managerlist, account_data)
    a.show()

    pcs1 = Process(target = Receiver.Receiver, args = (subStocks, stg_option, qlist, managerlist, account_data), daemon = True).start()
    pcs3 = Process(target = ExecChecker.Checker, args = (subStocks, stg_option, qlist, managerlist, account_data), daemon=True).start()
    pcs4 = Process(target = Order.Order, args = (subStocks, stg_option, qlist, managerlist, account_data), daemon=True).start()
    pcs2 = Process(target=STG1.Strategy, args=(subStocks, stg_option, qlist, managerlist, account_data), daemon=True).start()

    app.exec_()
