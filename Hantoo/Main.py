import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import configparser
from multiprocessing import *
import pprint
import os
import Token
import quantbox
from pykrx import stock
import pandas as pd
import datetime
import Receiver
import ExecChecker
import Strategy
import Order
import json
import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler

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
        print(f'보유종목 리스트 >> {self.BuyList}')

    def btn5(self):
        print('전량청산시작')
        for stockCode in self.PositionManager.keys():
            buyQty = self.PositionManager[stockCode]['보유수량']
            if buyQty > 0:
                signalName = '전량청산'
                self.OrderQ.put((stockCode, '매도', 'market',0, self.PositionManager[stockCode]['보유수량'], signalName))

    def btn6(self):
        pprint.pprint(dict(self.BalanceManager))

    def btn7(self):
        pprint.pprint(dict(self.PriceManger))

    def btn8(self):
        pprint.pprint(dict(self.TradingManager))
        print('보유종목 리스트 >> ', self.BuyList)

    def btn9(self):
        print('테스트매수')
        self.OrderQ.put(('test', '122630', '매수', 'market', 0, 10, '테스트'))


    def btn11(self):
        print('테스트매도')
        self.OrderQ.put(('test', '122630', '매도', 'market', 0, 10, '테스트'))

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

def get_key(stg_name):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    app_key = config[stg_name]['app_key']
    secret_key = config[stg_name]['secret_key']
    acc_num = config[stg_name]['acc_num']
    id = config[stg_name]['id']
    return app_key, secret_key, acc_num, id

def QuitAPP(app):
    app.quit()

def getData(frdate, todate, witID, universe = []):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    id = config['퀀트박스']['ID']
    pw = config['퀀트박스']['PW']
    quantbox.set_credentials(id, pw)
    data = quantbox.get_wit(witID, from_date = frdate, to_date = todate, stock_codes=universe)['result']
    data = data[witID]
    bsDate = stock.get_previous_business_days(fromdate=data.index[0], todate=data.index[-1])
    data.index = pd.to_datetime(data.index)

    return data.loc[bsDate]

def CreateUniverse(frdate, todate, witID, universe):
    while True:
        try:
            cond_df = getData(frdate, todate, witID, universe)
            universe = cond_df[cond_df == True].iloc[-1].dropna()
            break
        except:
            print('\n======================== 유니버스 재구성 ========================\n')
            continue

    return list(universe.keys())

def GetHoldingList(stg_name):
    try:
        with open(f'log/{stg_name}_보유현황.json' ,'r') as file:
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

    try:
        os.remove('token.dat')
    except FileNotFoundError:
        pass

    frdate = (datetime.datetime.now() - datetime.timedelta(days = 10)).strftime('%Y%m%d')
    todate = datetime.datetime.today().strftime('%Y%m%d')   ### todate는 반드시 오늘 이전으로 설정해야함함

    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    config = config['투자전략']
    stg_name = config['전략이름']
    buyCond_id = config['매수조건']
    sellCond_id = config['매도조건']
    motoo = config['모투']

    totalBetSize = int(config['totalBetSize']) # 총자산대비 투자비중
    maxCnt = int(config['maxCnt'])  # 최대 보유종목수
    buyOption = config['buyOption']  # 매수옵션
    sellOption = config['sellOption']  # 매도옵션
    rebal = int(config['rebal'])  # 리밸런싱 기간
    fee = float(config['fee'])  # 수수료

    stg_option = dict(전략명=stg_name, 총자산대비투자비중=totalBetSize / 100, 최대보유종목수=maxCnt, 리밸런싱=rebal, 수수료=fee, 매수옵션=buyOption,
                      매도옵션=sellOption)

    print('\n======================== 투자전략 분석중 ========================\n')

    # subStocks = ['122630','305540']   #### 테스트 코드
    # exitList = subStocks.copy()       #### 테스트 코드드

    HoldingList = GetHoldingList(stg_name)
    print(f'보유종목수 >> {len(HoldingList)}')
    if len(HoldingList) == 0:
        TradingList = CreateUniverse(frdate, todate, buyCond_id, universe=[])
        exitList = []
        availcnt = min(stg_option['최대보유종목수'], len(TradingList))
        addStocks = list(np.random.choice(TradingList, min(len(TradingList), availcnt), replace = False))    # 보유종목수가 0개면 매수조건을 충족하는 종목중에서 최대보유종목수만큼 랜덤으로 매수종목을 지정

    elif stg_option['최대보유종목수'] > len(HoldingList) and len(HoldingList) > 0:
        exitList = CreateUniverse(frdate, todate, sellCond_id, universe = HoldingList)
        TradingList = CreateUniverse(frdate, todate, buyCond_id, universe=[])
        addStockHubo = list(set(TradingList) - set(HoldingList + exitList))
        availcnt = stg_option['최대보유종목수'] - len(HoldingList)
        print(f'트레이딩리스트 갯수 >> {len(TradingList)}, 매수가능갯수 >> {availcnt}, 후보군 갯수 >> {len(addStockHubo)}')
        addStocks = list(np.random.choice(addStockHubo, min(len(TradingList), availcnt), replace = False))    # 보유종목수가 최대보유종목수보다 적으면 매수조건을 충족하는 종목중에서 n개의 신규종목을 편입

    elif stg_option['최대보유종목수'] == len(HoldingList) and len(HoldingList)> 0:
        exitList = CreateUniverse(frdate, todate, sellCond_id, universe = HoldingList)
        TradingList = [] # 신규로 편입할 종목수가 0개 이므로 매수조건을 충족하는 종목 리스트를 안가져와도 됌
        addStocks = []  # 신규로 편입할 종목수가 0개

    TotalSubStocks = HoldingList + addStocks + exitList
    TotalSubStocks = list(set(TotalSubStocks))

    # HoldingList : 현재 보유중인 종목 리스트
    # TradingList : 매수조건을 충족하는 종목 리스트
    # addStocks : 현재 보유종목수가 최대보유종목수보다 적어서 신규로 편입할 예정인 종목 리스트
    # exitList : 현재 보유종목중에 매도조건을 충족하여 청산해야 하는 종목 리스트


    print('\n======================== 투자전략 분석 완료 ========================\n')

    print(f'보유종목 리스트 >> {HoldingList}')
    print(f'청산종목 리스트 >> {sorted(exitList)}')
    print(f'추가종목 리스트 >> {sorted(addStocks)}')

    Token.Token(stg_name).get_access_token()  # 토큰부터 업데이트

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    if motoo == '실투' : motoo = False
    elif motoo == '모투' : motoo = True

    app_key, secret_key, acc_num, id = get_key(stg_name)
    account_data = [app_key, secret_key, acc_num, id, motoo]

    app = QApplication(sys.argv)
    a = Main(stg_option, qlist, managerlist, account_data)
    a.show()

    pcs1 = Process(target = Receiver.Receiver, args = (TotalSubStocks, stg_option, qlist, managerlist, account_data), daemon = True).start()
    pcs3 = Process(target = ExecChecker.Checker, args = (TotalSubStocks, stg_option, qlist, managerlist, account_data), daemon=True).start()
    pcs4 = Process(target = Order.Order, args = (TotalSubStocks, stg_option, qlist, managerlist, account_data), daemon=True).start()
    pcs2 = Process(target = Strategy.Strategy, args=(TotalSubStocks, exitList, stg_option, qlist, managerlist, account_data), daemon=True).start()

    schedular = BackgroundScheduler(timezone='Asia/Seoul', job_defaults={'max_instances': 10})
    schedular.start()
    schedular.add_job(QuitAPP, args = (app, ), trigger='cron', hour = '15', minute = '32')


    app.exec_()
