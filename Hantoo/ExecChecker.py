import os
from multiprocessing import *
import Logger
import configparser
import json
from PyQt5.QtTest import *
import datetime
import pprint
from pandas.tseries.offsets import BDay

config = configparser.ConfigParser()
config.read('config.ini', encoding='UTF-8')

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

class Checker:
    def __init__(self, subStocks, stg_option, Qlist, managerList, account_data):
        print('===== Exec Checker Start =====')
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

        self.stg_option = stg_option
        self.stg_name = self.stg_option['전략명']
        self.subStocks = subStocks

        self.logger = Logger.Logger()
        self.ExecChecker()

    def ExecChecker(self):
        while True:
            resp = self.ExecQ.get()

            pprint.pprint(resp)
            self.logger.add_log(resp, f'{self.stg_name}_체결내역')

            execGubun = resp['체결여부']  ### 1이면 주문접수, 2이면 체결데이터

            if execGubun == '1':
                continue

            QTest.qWait(250)
            orderID = str(int(resp['주문번호']))
            side = resp['매도매수구분']  #### 01 이면 매도, 02 면 매수
            stockCode = resp['주식단축종목코드']
            execQty = int(resp['체결수량'])
            execPrice = float(resp['체결단가'])
            execTime = resp['주식체결시간']
            orderQty = float(resp['주문수량'])
            try:
                orderPrice = float(resp['주문가격'])
            except:
                orderPrice = 0

            today = datetime.datetime.now()
            adj_time2 = datetime.datetime.strptime(execTime, '%H%M%S')
            execTime = datetime.datetime(today.year, today.month, today.day, adj_time2.hour,
                                         adj_time2.minute, adj_time2.second)

            # 가끔 주문시 주문번호와 체결데이터로 수신한 주문번호가 맞지 않음

            if orderID not in self.ExecManager:
                self.ExecManager[orderID] = dict(종목코드=stockCode, 매수도구분=side,
                                                 체결시간=execTime, 주문가격=orderPrice, 주문수량=orderQty,
                                                 평균체결가격=execPrice, 누적체결수량=execQty, 미체결수량=orderQty - execQty)

            else:
                avgExecPrice = self.ExecManager[orderID]['평균체결가격']
                cumExecQty = self.ExecManager[orderID]['누적체결수량']

                ExecManager_update = self.ExecManager[orderID]
                ExecManager_update['체결시간'] = execTime
                ExecManager_update['평균체결가격'] = ((avgExecPrice * cumExecQty) + (execPrice * execQty)) / (
                            cumExecQty + execQty)
                ExecManager_update['누적체결수량'] = cumExecQty + execQty
                ExecManager_update['미체결수량'] = self.ExecManager[orderID]['주문수량'] - cumExecQty - execQty

                self.ExecManager.update({orderID: ExecManager_update})

            if self.ExecManager[orderID]['미체결수량'] == 0:

                if stockCode not in self.subStocks:  # 감시종목이 아닌 종목의 체결데이터가 오면 텔레그램 시그널만 발송함
                    tele_msg = f"[매수 (감시종목아님)]\n" \
                               f"- 시간 : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                               f"- 전략이름 : {self.stg_name}\n" \
                               f"- 종목코드 : {stockCode}\n" \
                               f"- 매수가격 : {self.PositionManager[stockCode]['평균매수가격']}\n" \
                               f"- 매수수량 : {self.PositionManager[stockCode]['보유수량']}\n"
                    self.logger.telegram_bot(self.stg_name, tele_msg)
                    continue

                PositionManager_update = self.PositionManager[stockCode]
                if side == '02':  # 매수
                    PositionManager_update['평균매수가격'] = self.ExecManager[orderID]['평균체결가격']
                    PositionManager_update['보유수량'] = self.ExecManager[orderID]['누적체결수량']
                    PositionManager_update['주문번호'] = orderID
                    PositionManager_update['매수날짜'] = datetime.datetime.today().strftime('%Y%m%d')
                    PositionManager_update['매도예정날짜'] = (datetime.datetime.today() + BDay(self.stg_option['리밸런싱'])).strftime('%Y%m%d')
                    self.PositionManager.update({stockCode: PositionManager_update})

                    record = dict(체결시간=datetime.datetime.now(), 종목코드=stockCode, 매수도구분=side,
                                  평균체결가격=self.ExecManager[orderID]['평균체결가격'],
                                  누적체결수량=self.ExecManager[orderID]['누적체결수량'],
                                  주문가격=orderPrice, 주문수량=orderQty, 수익률=0, 수익금=0)
                    self.logger.add_log(record, f'{self.stg_name}_매매내역')

                    tele_msg = f"[매수]\n" \
                               f"- 시간 : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                               f"- 전략이름 : {self.stg_name}\n" \
                               f"- 종목코드 : {stockCode}\n" \
                               f"- 매수가격 : {self.PositionManager[stockCode]['평균매수가격']}\n" \
                               f"- 매수수량 : {self.PositionManager[stockCode]['보유수량']}\n"
                    self.logger.telegram_bot(self.stg_name, tele_msg)
                    if stockCode not in self.BuyList:
                        self.BuyList.append(stockCode)
                    with open(f'log/{self.stg_name}_보유현황.json', 'w') as json_file:
                        json.dump(self.PositionManager, json_file, default=str)

                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매수주문여부'] = False
                    TradingManager_update['매수주문정정'] = False
                    self.TradingManager.update({stockCode: TradingManager_update})

                else:
                    if self.PositionManager[stockCode]['평균매수가격'] == 0:
                        continue
                    profit = round(
                        self.ExecManager[orderID]['평균체결가격'] / self.PositionManager[stockCode]['평균매수가격'] - 1,
                        4)
                    profit_amount = round(
                        (self.ExecManager[orderID]['평균체결가격'] - self.PositionManager[stockCode]['평균매수가격']) *
                        self.ExecManager[orderID]['누적체결수량'])

                    record = dict(체결시간=datetime.datetime.now(), 종목코드=stockCode, 매수도구분=side,
                                  평균체결가격=self.ExecManager[orderID]['평균체결가격'],
                                  누적체결수량=self.ExecManager[orderID]['누적체결수량'],
                                  주문가격=orderPrice, 주문수량=orderQty, 수익률=profit, 수익금=profit_amount)
                    self.logger.add_log(record, f'{self.stg_name}_매매내역')

                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매수주문번호'] = 0
                    self.TradingManager.update({stockCode: TradingManager_update})

                    tele_msg = f"[매도]\n" \
                               f"- 시간 : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                               f"- 전략이름 : {self.stg_name}\n" \
                               f"- 종목코드 : {stockCode}\n" \
                               f"- 매도가격 : {self.ExecManager[orderID]['평균체결가격']}\n" \
                               f"- 매도수량 : {self.ExecManager[orderID]['누적체결수량']}\n"

                    PositionManager_update['평균매수가격'] = 0
                    PositionManager_update['보유수량'] = 0
                    PositionManager_update['주문번호'] = 0
                    PositionManager_update['매도날짜'] = datetime.datetime.today().strftime('%Y%m%d')
                    self.PositionManager.update({stockCode: PositionManager_update})
                    with open(f'log/{self.stg_name}_보유현황.json', 'w') as json_file:
                        json.dump(self.PositionManager, json_file, default=str)

                    self.logger.telegram_bot(self.stg_name, tele_msg)
                    self.BuyList.remove(stockCode)

                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = False
                    TradingManager_update['매도주문정정'] = False
                    TradingManager_update['매도날짜'] = datetime.datetime.today().strftime('%Y%m%d')
                    TradingManager_update['매수예정날짜'] = (datetime.datetime.today() + BDay(1)).strftime('%Y%m%d')
                    self.TradingManager.update({stockCode: TradingManager_update})
                    self.BalanceManager.update({'주문가능현금': self.BalanceManager['주문가능현금'] + profit_amount})

                    pprint.pprint(dict(self.BalanceManager))



if __name__ == '__main__':
    motoo = True
    # Token.Token(motoo).get_access_token()  # 토큰부터 업데이트,

    buyCond_id = 'c94aab2a2abc4f889d4eeba5af6cfcc9'
    sellCond_id = '950dd29001c2447e836fe24e86789c9d'

    frdate = '20230701'
    todate = '20230731'

    stg_name = '테스트'  # 전략이름
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

    subStocks = ['005930','233740']

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    app_key, secret_key, acc_num, id = get_key(motoo)
    account_data = [app_key, secret_key, acc_num, id, motoo]

    Checker(subStocks, stg_option, qlist, managerlist, account_data)