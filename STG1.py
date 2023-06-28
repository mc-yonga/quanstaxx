from multiprocessing import *
import configparser
import pprint
import datetime
import numpy as np
import json
from hoga import *

class Strategy:
    def __init__(self, Qlist, managerList, account_data, stg_name):
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

        self.OpenCutManager = dict()
        self.TodayUniverse = list()

        self.stg_name = stg_name
        self.UpdatePositionManager()
        self.Observer()

    def UpdatePositionManager(self):
        try:
            with open(f'log/{self.stg_name}_보유현황.json' ,'r') as file:
                position = json.load(file)
            position = eval(position)

            for stockCode in position.keys():
                if position[stockCode]['보유수량'] > 0:
                    PositionManager_update = self.PositionManager[stockCode]
                    PositionManager_update['평균매수가격'] = position[stockCode]['평균매수가격']
                    PositionManager_update['보유수량'] = position[stockCode]['보유수량']
                    PositionManager_update['주문번호'] = position[stockCode]['주문번호']
                    PositionManager_update['종목명'] = position[stockCode]['종목명']
                    self.PositionManager.update({stockCode : PositionManager_update})
                    self.BuyList.append(stockCode)
            pprint.pprint(dict(self.PositionManager))
        except:
            print('아직 매매내역이 없음')

    def Observer(self):
        while True:
            now = datetime.datetime.now().strftime('%H%M%S')
            market_start = '090000'
            dongsihoga = '152000'
            market_end = '153000'

            if self.PriceQ.empty():
                continue

            data = self.PriceQ.get()
            stockCode = data['종목코드']


            PriceManager_update = self.PriceManger[stockCode]

            ys_open = self.TradingManager[stockCode]['전일시가']
            ys_high = self.TradingManager[stockCode]['전일고가']

            if now < market_start:  ### 개장전
                if data['TRID'] != 'H0STASP0' :
                    continue

                expacPrice = abs(float(data['예상체결가']))
                expacQty = abs(float(data['예상체결수량']))

                if self.PositionManager[stockCode]["보유수량"] == 0 and self.TradingManager[stockCode]['조건충족여부'] == True and self.TradingManager[stockCode]['매수주문여부'] == False: ### 보유수량은 없고, 매수주문한적 없고, 전일 고가 == 전일시가이면 시가매수
                    if self.BalanceManager['순자산금액'] < self.BalanceManager['총평가금액'] / len(self.TradingManager.keys()):
                        print('[장전 시가매수] 순자산금액이 부족하여 시가매수를 할 수 없음')
                    else:
                        # orderQty = (self.BalanceManager['총평가금액'] / len(self.TradingManager.keys())) / expacPrice - 1
                        orderQty = 10
                        signalName = '장전시가매수'
                        self.OrderQ.put((stockCode, '매수', 'market', 0, orderQty, signalName))
                        TradingManager_update = self.TradingManager[stockCode]
                        TradingManager_update['매수주문여부'] = True
                        self.TradingManager.update({stockCode : TradingManager_update})

                elif self.TradingManager[stockCode]["매수주문여부"] == True and self.PositionManager[stockCode]["보유수량"] == 0:   ### 매수주문은 했는데 보유수량이 0이면
                    if expacPrice != self.PriceManger[stockCode]['예상체결가']: ### 예상체결가격이 변했으면 주문수량을 정정해야 함
                        orgID = self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["한국거래소주문조직번호"]
                        adj_OrderQty = (self.BalanceManager['총평가금액'] / len(self.TradingManager.keys())) / expacPrice - 1
                        signalName = '장전매수주문수정'
                        self.OrderQ.put((orgID, self.TradingManager[stockCode]["매수주문번호"], '01', 0, adj_OrderQty, True, signalName))
                        print(f'[시가매수 정정] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, {self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["주문수량"]} >> {adj_OrderQty} 주문수량 수정')

                    else:
                        orderQty = self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]['주문수량']
                        print(f'[시가매수대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 주문수량 {orderQty}')

                elif self.TradingManager[stockCode]['매도주문번호'] == 0 and self.PositionManager[stockCode]["보유수량"] != 0 and self.TradingManager[stockCode]['매도주문여부'] == False and self.TradingManager[stockCode]['조건충족여부'] == False:  # 보유수량이 있는데 매도주문을 안걸었으면 시가매도
                    ### 포지션 보유중인데 조건을 충족하지 않으면 시가매도청산
                    print(stockCode,'시가매도 시작')
                    signalName = '시가매도'
                    self.OrderQ.put((stockCode, '매도', 'market', 0, self.PositionManager[stockCode]["보유수량"], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})

                elif self.PositionManager[stockCode]["보유수량"] > 0 and self.TradingManager[stockCode]['매도주문여부'] == True: # 보유수량이 있는데 매도주문을 걸었으면 시가매도대기
                    expacProfit = expacPrice / self.PositionManager[stockCode]['평균매수가격'] - 1
                    expacProfit = round(expacProfit * 100, 4)
                    print(f'[시가매도대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 예상수익률 : {expacProfit}%')
                else:
                    print(f'[개장전] 종목코드 >> {stockCode}, 전일고가 >> {self.TradingManager[stockCode]["전일고가"]}, 전일저가 >> {self.TradingManager[stockCode]["전일저가"]}')

                PriceManager_update['예상체결가'] = expacPrice
                PriceManager_update['예상체결수량'] = expacQty

            elif now > market_start and now < dongsihoga:
                if data['TRID'] != 'H0STCNT0':
                    continue

                dayopen = abs(float(data['당일시가']))
                dayhigh = abs(float(data['당일고가']))
                daylow = abs(float(data['당일저가']))
                currentPrice = abs(float(data['현재가']))

                if currentPrice == self.PriceManger[stockCode]['현재가']:
                    continue

                if stockCode not in self.BuyList and self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys() and self.TradingManager[stockCode]['매수주문정정'] == False:
                    gap = datetime.datetime.now() - self.TradingManager[stockCode]['매수주문시간']
                    buyOrderID = self.TradingManager[stockCode]['매수주문번호']

                    if self.TradingManager[stockCode]['매수주문번호'] in self.ExecManager.keys():
                        print(f'[매수 미체결] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")},'
                              f' 종목코드 : {stockCode},'
                              f' 미체결시간 : {gap} '
                              f' 주문가격 : {self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["주문가격"]},'
                              f' 주문수량 : {self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["주문수량"]}'
                              f' 평균매수가격 : {self.ExecManager[self.TradingManager[stockCode]["매수주문번호"]]["평균체결가격"]},'
                              f' 누적체결수량 : {self.ExecManager[self.TradingManager[stockCode]["매수주문번호"]]["누적체결수량"]},'
                              f' 미체결수량 : {self.ExecManager[self.TradingManager[stockCode]["매수주문번호"]]["미체결수량"]}')

                    else:
                        print(f'[매수 미체결 - 하나도 체결안됨] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")},'
                              f' 종목코드 : {stockCode},'
                              f' 미체결시간 : {gap} '
                              f' 주문가격 : {self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["주문가격"]},'
                              f' 주문수량 : {self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["주문수량"]}')

                elif stockCode in self.BuyList and self.PositionManager[stockCode]["평균매수가격"] > 0:
                    profit = currentPrice / self.PositionManager[stockCode]["평균매수가격"] - 1
                    profit = round(profit, 4)

                    print(f'[보유중] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 평균매수가격 : {self.PositionManager[stockCode]["평균매수가격"]}, 매수수량 : {self.PositionManager[stockCode]["보유수량"]}, 수익률 : {profit}')

                    ###### 매도 테스트 코드 ########
                    # signalName = '보유종목청산'
                    # if self.TradingManager[stockCode]['매도주문여부'] == False:
                    #     self.OrderQ.put((stockCode, '매도', 'market', 0, 10, signalName))
                    #     TradingManager_update = self.TradingManager[stockCode]
                    #     TradingManager_update['매도주문여부'] = True
                    #     self.TradingManager.update({stockCode : TradingManager_update})

                PriceManager_update['당일시가'] = dayopen
                PriceManager_update['당일고가'] = dayhigh
                PriceManager_update['당일저가'] = daylow
                PriceManager_update['현재가'] = currentPrice

            elif now > dongsihoga and now < market_end:  ### 3시 20분 동시호가부터 장 마감할떄까지
                if data['TRID'] != 'H0STASP0' :
                    continue

                if stockCode not in self.BuyList:
                    print(f'[동시호가] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, {stockCode}는 보유종목이 아닙니다')
                    continue
                else:
                    expacPrice = abs(float(data['예상체결가']))
                    profit = expacPrice / self.PositionManager[stockCode]["평균매수가격"] - 1
                    profit = round(profit, 4)
                    print(f'[동시호가] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 평균매수가격 : {self.PositionManager[stockCode]["평균매수가격"]}, 매수수량 : {self.PositionManager[stockCode]["보유수량"]}, 수익률 : {profit}')

            self.PriceManger.update({stockCode : PriceManager_update})


def get_key(motoo: bool):
    config = configparser.ConfigParser()
    config.read('../ignore/config.ini', encoding='utf-8')

    if motoo == True:
        name = 'motoo'
    else:
        name = 'real'

    app_key = config[f'{name}_trading']['app_key']
    secret_key = config[f'{name}_trading']['secret_key']
    acc_num = config[f'{name}_trading']['acc_num']
    id = config[f'{name}_trading']['id']

    return app_key, secret_key, acc_num, id, motoo
if __name__ == '__main__':
    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    app_key, secret_key, acc_num, id, motoo = get_key(True)
    account_data = [app_key, secret_key, acc_num, id, motoo]
    strategy_name = '테스트'

    Strategy(qlist, managerlist, account_data, strategy_name)




