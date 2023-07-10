from multiprocessing import *
import mojito
import configparser
import requests
import json
import datetime
import pickle
import Logger
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
import sys
import pprint
from PyQt5.QtTest import *

class OrderSignal(QThread):
    CreateMarketOrder = pyqtSignal(str, str, int, int, str)
    CreateLimitOrder = pyqtSignal(str, str, int, int, str)
    EditOrder = pyqtSignal(str, str, str, int, int, bool, str)
    CancelOrder = pyqtSignal(str, str, int, bool, str, int)


    def __init__(self, main):
        super().__init__()
        self.main = main

    def run(self):
        print('Order Signal Start')
        while True:
            if self.main.OrderQ.empty():
                continue

            data = self.main.OrderQ.get()
            print(data)

            if len(data) == 6:
                stockCode, side, orderType, orderPrice, orderQty, signalName = data
                if orderType == 'market':
                    self.CreateMarketOrder.emit(stockCode, side, orderPrice, orderQty, signalName)
                elif orderType == 'limit':
                    self.CreateLimitOrder.emit(stockCode, side, orderPrice, orderQty, signalName)

class Order:
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

        self.broker = mojito.KoreaInvestment(
            api_key = self.app_key,
            api_secret = self.secret_key,
            acc_no = self.acc_num,
            mock = self.motoo
            )

        self.BalanceManagerUpdate()
        app = QApplication(sys.argv)

        self.stg_name = stg_name
        self.logger = Logger.Logger()
        self.orderSignal = OrderSignal(self)
        self.orderSignal.CreateMarketOrder.connect(self.CreateMarketOrder)
        self.orderSignal.CreateLimitOrder.connect(self.CreateLimitOrder)
        self.orderSignal.start()

        app.exec_()

        if self.motoo == False:
            self.base_url = 'https://openapi.koreainvestment.com:9443'
        else:
            self.base_url = 'https://openapivts.koreainvestment.com:29443'

        try:
            with open("token.dat", "rb") as f:
                data = pickle.load(f)
                self.access_token = f'Bearer {data["access_token"]}'
        except:
            self.GetAccessToken()
            # pass

    def BalanceManagerUpdate(self):
        resp = self.BalanceInfo()
        pprint.pprint(resp)
        for key, value in resp.items():
            self.BalanceManager.update({key : value})
        print('밸런스 매니저 업데이트 완료')

    def GetAccessToken(self):
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.secret_key}
        PATH = "oauth2/tokenP"
        URL = f"{self.base_url}/{PATH}"
        res = requests.post(URL, headers=headers, data=json.dumps(body))
        ACCESS_TOKEN = res.json()["access_token"]
        return ACCESS_TOKEN

    def CreateMarketOrder(self, stockCode, side, orderPrice, orderQty, signalName):
        if side == '매수':
            resp = self.broker.create_market_buy_order(stockCode, orderQty)
        else:
            resp = self.broker.create_market_sell_order(stockCode, orderQty)
        QTest.qWait(250)

        if resp['rt_cd'] != '0':
            tele_msg = f'[주문오류]\n' \
                       f'- 전략이름 : {self.stg_name}\n' \
                       f'- 종목코드 : {stockCode}\n' \
                       f'- 주문가격 : {orderPrice}\n' \
                       f'- 주문수량 : {orderQty}\n' \
                       f'- 오류메세지 : {resp["msg1"]}'
            self.logger.telegram_bot('에러봇', tele_msg)
        else:
            order_time = resp['output']['ORD_TMD']
            adj_time2 = datetime.datetime.strptime(order_time,'%H%M%S')
            today = datetime.datetime.now()
            orderTime = datetime.datetime(today.year, today.month, today.day, adj_time2.hour, adj_time2.minute, adj_time2.second)
            orderID = str(int(resp['output']['ODNO']))
            orderComID = str(int(resp['output']['KRX_FWDG_ORD_ORGNO']))
            orderPrice = 0

            result = dict(주문시각 = orderTime, 주문번호 = orderID, 한국거래소전송주문조직번호 = orderComID, 매수도구분 = side,
                          종목코드 = stockCode, 주문가격 = orderPrice, 주문수량 = orderQty, 주문명 = signalName, 주문타입 = '01')

            print('\n==========시장가 주문완료===========')
            pprint.pprint(result)
            print('')

            self.logger.add_log(result, f'{self.stg_name}_주문내역')

            TradingManager_update = self.TradingManager[stockCode]
            TradingManager_update[f'{side}주문번호'] = orderID
            self.TradingManager.update({stockCode : TradingManager_update})

            if orderID not in self.OrderManager.keys():
                self.OrderManager[orderID] = result
            else:
                order_manager_update = self.OrderManager[orderID]
                order_manager_update['주문시각'] = result['주문시각']
                order_manager_update['한국거래소전송주문조직번호'] = result['한국거래소전송주문조직번호']
                order_manager_update['매수도구분'] = side
                order_manager_update['종목코드'] = stockCode
                order_manager_update['주문가격'] = result['주문가격']
                order_manager_update['주문수량'] = result['주문수량']
                order_manager_update['주문명'] = signalName
                order_manager_update['주문구분'] = '01'

                self.OrderManager.update({orderID : order_manager_update})

            QTest.qWait(1000)
            if side == '매수':
                balance_info = self.BalanceInfo()
                for key, value in balance_info.items():
                    self.BalanceManager.update({key: value})
                pprint.pprint(dict(self.BalanceManager))

    def CreateLimitOrder(self, stockCode, side, orderPrice, orderQty, signalName):
        if side == '매수':
            resp = self.broker.create_limit_buy_order(stockCode, orderPrice, orderQty)
        else:
            resp = self.broker.create_limit_sell_order(stockCode, orderPrice, orderQty)
        QTest.qWait(250)

        if resp['rt_cd'] != '0':
            tele_msg = f'[주문오류]\n' \
                       f'- 전략이름 : {self.stg_name}\n' \
                       f'- 종목코드 : {stockCode}\n' \
                       f'- 주문가격 : {orderPrice}\n' \
                       f'- 주문수량 : {orderQty}\n' \
                       f'- 오류메세지 : {resp["msg1"]}'
            self.logger.telegram_bot('에러봇', tele_msg)
        else:
            order_time = resp['output']['ORD_TMD']
            adj_time2 = datetime.datetime.strptime(order_time,'%H%M%S')
            today = datetime.datetime.now()
            orderTime = datetime.datetime(today.year, today.month, today.day, adj_time2.hour, adj_time2.minute, adj_time2.second)
            orderID = str(int(resp['output']['ODNO']))
            orderComID = str(int(resp['output']['KRX_FWDG_ORD_ORGNO']))

            result = dict(주문시각 = orderTime, 주문번호 = orderID, 한국거래소전송주문조직번호 = orderComID, 매수도구분 = side,
                          종목코드 = stockCode, 주문가격 = orderPrice, 주문수량 = orderQty, 주문명 = signalName, 주문타입 = '00')

            print('\n==========지정가 주문완료===========')
            pprint.pprint(result)
            print('')

            self.logger.add_log(result, f'{self.stg_name}_주문내역')

            TradingManager_update = self.TradingManager[stockCode]
            TradingManager_update[f'{side}주문번호'] = orderID
            self.TradingManager.update({stockCode : TradingManager_update})

            if orderID not in self.OrderManager.keys():
                self.OrderManager[orderID] = result
            else:
                order_manager_update = self.OrderManager[orderID]
                order_manager_update['주문시각'] = result['주문시각']
                order_manager_update['한국거래소전송주문조직번호'] = result['한국거래소전송주문조직번호']
                order_manager_update['매수도구분'] = side
                order_manager_update['종목코드'] = stockCode
                order_manager_update['주문가격'] = result['주문가격']
                order_manager_update['주문수량'] = result['주문수량']
                order_manager_update['주문명'] = signalName
                order_manager_update['주문구분'] = '00'

                self.OrderManager.update({stockCode : order_manager_update})

            QTest.qWait(1000)
            if side == '매수':
                balance_info = self.BalanceInfo()
                for key, value in balance_info.items():
                    self.BalanceManager.update({key: value})
                pprint.pprint(dict(self.BalanceManager))

    def ModifyOrder(self, orgID, orderID, orderType, orderPrice, orderQty, total, signalName):
        """
        :param orgID: 주식일별주문체결조회 API output1의 odno(주문번호) 값 입력, 주문시 한국투자증권 시스템에서 채번된 주문번호
        :param orderID:
        :param order_type: '00' : 지정가, '01' : 시장가,
        :param price: 가격
        :param quantity : 수량
        :param total: True (잔량전부), False (잔량일부)
        :return:
        """
        resp = self.broker.modify_order(orgID, orderID, orderType, orderPrice, orderQty, total)
        print('====== 주문수정 #######')
        pprint.pprint(resp)
        QTest.qWait(250)
        stockCode = self.OrderManager[orderID]["종목코드"]
        if resp['rt_cd'] != '0':
            tele_msg = f'[주문오류 (정정)]\n' \
                       f'- 전략이름 : {self.stg_name}\n' \
                       f'- 종목코드 : {stockCode}\n' \
                       f'- 주문가격 : {orderPrice}\n' \
                       f'- 주문수량 : {orderQty}\n' \
                       f'- 오류메세지 : {resp["msg1"]}'
            self.logger.telegram_bot('에러봇', tele_msg)
        else:
            order_time = resp['output']['ORD_TMD']
            adj_time2 = datetime.datetime.strptime(order_time, '%H%M%S')
            today = datetime.datetime.now()
            orderTime = datetime.datetime(today.year, today.month, today.day, adj_time2.hour,
                                          adj_time2.minute, adj_time2.second)
            orderID = str(int(resp['output']['ODNO']))
            orderComID = str(int(resp['output']['KRX_FWDG_ORD_ORGNO']))

            result = dict(주문시각=orderTime, 주문번호=orderID, 한국거래소전송주문조직번호=orderComID, 매수도구분='',
                          종목코드=stockCode, 주문가격=orderPrice, 주문수량=orderQty, 주문명=signalName, 주문구분=orderType)

            self.logger.add_log(result, f'{self.stg_name}_주문내역')

            TradingManager_update = self.TradingManager[stockCode]

            TradingManager_update[
                f'{self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]["매수도구분"]}주문번호'] = orderID
            self.TradingManager.update({stockCode: TradingManager_update})

            if orderID not in self.OrderManager.keys():
                self.OrderManager[orderID] = result
            else:
                order_manager_update = self.OrderManager[orderID]
                order_manager_update['주문시각'] = result['주문시각']
                order_manager_update['한국거래소전송주문조직번호'] = result['한국거래소전송주문조직번호']
                order_manager_update['매수도구분'] = self.OrderManager[orderID]["매수도구분"]
                order_manager_update['종목코드'] = stockCode
                order_manager_update['주문가격'] = result['주문가격']
                order_manager_update['주문수량'] = result['주문수량']
                order_manager_update['주문명'] = signalName
                order_manager_update['주문구분'] = orderType

                self.OrderManager.update({stockCode: order_manager_update})

            balance_info = self.BalanceInfo()
            for key, value in balance_info.items():
                self.BalanceManager.update({key: value})

    def GetPosition(self):
        balance = self.GetBalance()
        balance_output1 = balance['output1']
        holding_tickers = {}

        for data in balance_output1:
            stock_name = data['prdt_name']
            avg_buy_price = float(data['pchs_avg_pric'])
            quantity = int(data['hldg_qty'])
            value = float(data['evlu_amt'])
            value_pl_ratio = float(data['evlu_pfls_rt'])
            value_pl_won = float(data['evlu_pfls_amt'])
            stock_code = data['pdno']
            holding_tickers.update({stock_code : {'종목명' : stock_name,'평균매수가격' : avg_buy_price,'보유수량' : quantity, '평가금액' : value, '평가손익률' : value_pl_ratio / 100, '평가손익금액' : value_pl_won}})

        return  holding_tickers

    def GetBalance(self):
        return self.broker.fetch_balance()

    def BalanceInfo(self):
        balance = self.GetBalance()
        balance_output2 = balance['output2'][0]

        total_value_amount = float(balance_output2['tot_evlu_amt'])    # 총평가금액
        available_cash = float(balance_output2['prvs_rcdl_excc_amt'])        # 주문가능현금
        net_worth_won = float(balance_output2['nass_amt'])             # 순자산금액
        total_buy_amount = float(balance_output2['pchs_amt_smtl_amt']) # 총매입금액
        total_value_amount_after_buy = float(balance_output2['evlu_amt_smtl_amt'])   # 보유종목평가금액합계
        total_pl_amount = float(balance_output2['evlu_pfls_smtl_amt'])  # 손익금액합계
        balance_info = dict(총평가금액 = total_value_amount, 주문가능현금 = available_cash, 순자산금액 = net_worth_won, 총매입금액 = total_buy_amount, 보유종목평가금액합계 = total_value_amount_after_buy, 손익금액합계 = total_pl_amount)

        return balance_info

    def avail_buy_quantity(self, ticker, price, order_type):
        if order_type == 'market':
            order_type = '01'
        else:
            order_type = '00'
        resp = self.broker.check_buy_order(ticker, price, order_type)['output']
        max_buy_won = float(resp['max_buy_amt'])
        max_buy_quantity = float(resp['max_buy_qty'])
        avail_cash = float(resp['ord_psbl_cash'])
        avg_buy_price = float(resp['psbl_qty_calc_unpr'])
        data = dict(가능수량계산단가  = avg_buy_price, 최대매수금액 = max_buy_won, 최대매수수량 = max_buy_quantity, 주문가능현금 = avail_cash)

        return data

def get_key(motoo: bool):
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    if motoo == True:
        keyword = '모투'
    else:
        keyword = '실투'

    app_key = config[keyword]['app_key']
    secret_key = config[keyword]['secret_key']
    acc_num = config[keyword]['acc_num']
    id = config[keyword]['id']

    return app_key, secret_key, acc_num, id, motoo

if __name__ == '__main__':

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    motoo = True
    app_key, secret_key, acc_num, id, motoo = get_key(motoo = True)

    account_data = [app_key, secret_key, acc_num, id, motoo]

    a = Order(qlist, managerlist, account_data, '테스트')
    print(a)

