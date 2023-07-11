import os
import traceback

import websockets
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from multiprocessing import *
import Logger
import configparser
import requests
import json
from PyQt5.QtTest import *
import datetime
import pprint
from pandas.tseries.offsets import BDay

config = configparser.ConfigParser()
config.read('config.ini', encoding='UTF-8')

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

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

    return app_key, secret_key, acc_num, id


def get_approval(key, secret):
    """웹소켓 접속키 발급"""
    url = 'https://openapi.koreainvestment.com:9443'
    headers = {"content-type": "application/json"}
    body = {"grant_type": "client_credentials",
            "appkey": key,
            "secretkey": secret}
    PATH = "oauth2/Approval"
    URL = f"{url}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    approval_key = res.json()["approval_key"]
    return approval_key


def aes_cbc_base64_dec(key, iv, cipher_text):
    """
    :param key:  str type AES256 secret key value
    :param iv: str type AES256 Initialize Vector
    :param cipher_text: Base64 encoded AES256 str
    :return: Base64-AES256 decodec str
    """
    try:
        try:
            cipher = AES.new(key.encode('cp949'), AES.MODE_CBC, iv.encode('cp949'))
            return bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size))
        except:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            result = bytes.decode(unpad(cipher.decrypt(b64decode(cipher_text)), AES.block_size), 'utf-8',
                                  errors='replace')
            result = result.replace('\ufffd', '')
            return result

    except Exception as e:
        print(e)
        print(traceback.format_exc())
        Logger.Logger().add_log('', 'error')
        Logger.Logger().telegram_bot('에러봇', '복호화 과정에서 에러발생')


def OrderExecData(data, key, iv):
    # AES256 처리 단계

    aes_dec_str = aes_cbc_base64_dec(key, iv, data)
    pValue = aes_dec_str.split('^')

    if pValue[13] == '2':  # 체결통보
        print("#### 국내주식 체결 통보 ####")
        menulist = "고객ID|계좌번호|주문번호|원주문번호|매도매수구분|정정구분|주문종류|주문조건|주식단축종목코드|체결수량|체결단가|주식체결시간|거부여부|체결여부|접수여부|지점번호|주문수량|계좌명|체결종목명|신용구분|신용대출일자|체결종목명40|주문가격"
        menustr1 = menulist.split('|')
    else:
        print("#### 국내주식 주문·정정·취소·거부 접수 통보 ####")
        menulist = "고객ID|계좌번호|주문번호|원주문번호|매도매수구분|정정구분|주문종류|주문조건|주식단축종목코드|주문수량|주문가격|주식체결시간|거부여부|체결여부|접수여부|지점번호|주문수량|계좌명|주문종목명|신용구분|신용대출일자|체결종목명40|체결단가"
        menustr1 = menulist.split('|')

    data_list = {}
    min_len = min(len(pValue), len(menustr1))  #### pValue 갯수가 일정하게 들어오지 않음, 어떤때는 22개, 어떤때는 25개가 날라옴
    for i in range(min_len):  ### 그래서 pvalue와 mennustr1 갯수 중에서 작은 값을 for문 돌림
        data_list.update({menustr1[i]: pValue[i]})
    return data_list


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

        self.logger = Logger.Logger()
        self.ExecChecker()

    async def OrderExecWebsocket(self):
        APPROVAL_KEY = get_approval(self.app_key, self.secret_key)
        if self.motoo == True:
            url = 'ws://ops.koreainvestment.com:31000'  # 모의계좌
            tr_id = 'H0STCNI9'
        else:
            url = 'ws://ops.koreainvestment.com:21000'  # 모의계좌
            tr_id = 'H0STCNI0'

        code_list = ['1', tr_id, self.id]
        temp = '{"header":{"approval_key": "%s","custtype":"P","tr_type":"%s","content-type":"utf-8"},"body":{"input":{"tr_id":"%s","tr_key":"%s"}}}' % (
            APPROVAL_KEY, code_list[0], code_list[1], code_list[2])

        async with websockets.connect(url, ping_interval=None) as websocket:
            await websocket.send(temp)

            while True:
                if not websocket.open:
                    try:
                        websocket = await websocket.connect(url)
                        await websocket.send(temp)

                    except:
                        print('웹소켓 재연결 시도중 ...')

                data = await websocket.recv()

                if data[0] == '1':  # 실시간 데이터일 경우

                    recvstr = data.split('|')  # 수신데이터가 실데이터 이전은 '|'로 나뉘어져있어 split
                    trid0 = recvstr[1]
                    if trid0 == "K0STCNI0" or trid0 == "K0STCNI9" or trid0 == "H0STCNI0" or trid0 == "H0STCNI9":  # 주실체결 통보 처리
                        resp = OrderExecData(recvstr[3], aes_key, aes_iv)

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

                            if stockCode not in self.PositionManager.keys():  # 감시종목이 아닌 종목의 체결데이터가 오면 continue
                                continue
                            PositionManager_update = self.PositionManager[stockCode]
                            if side == '02':  # 매수
                                PositionManager_update['평균매수가격'] = self.ExecManager[orderID]['평균체결가격']
                                PositionManager_update['보유수량'] = self.ExecManager[orderID]['누적체결수량']
                                PositionManager_update['주문번호'] = orderID
                                PositionManager_update['매수날짜'] = datetime.datetime.today()
                                PositionManager_update['매도예정날짜'] = datetime.datetime.today() + BDay(self.stg_option['리밸런싱'])
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
                                PositionManager_update['매도날짜'] = datetime.datetime.now()
                                self.PositionManager.update({stockCode: PositionManager_update})
                                with open(f'log/{self.stg_name}_보유현황.json', 'w') as json_file:
                                    json.dump(self.PositionManager, json_file, default=str)

                                self.logger.telegram_bot(self.stg_name, tele_msg)
                                self.BuyList.remove(stockCode)

                                TradingManager_update = self.TradingManager[stockCode]
                                TradingManager_update['매도주문여부'] = False
                                TradingManager_update['매도주문정정'] = False
                                TradingManager_update['매도날짜'] = datetime.datetime.today()
                                TradingManager_update['매수예정날짜'] = datetime.datetime.today() + BDay(1)
                                self.TradingManager.update({stockCode: TradingManager_update})
                                self.BalanceManager.update({'주문가능현금': self.BalanceManager['주문가능현금'] + profit_amount})

                                pprint.pprint(dict(self.BalanceManager))

                else:
                    jsonObject = json.loads(data)
                    trid = jsonObject["header"]["tr_id"]

                    if trid != "PINGPONG":
                        rt_cd = jsonObject["body"]["rt_cd"]
                        if rt_cd == '1':  # 에러일 경우 처리
                            print("### 체결통보 ERROR RETURN CODE [ %s ] MSG [ %s ]" % (rt_cd, jsonObject["body"]["msg1"]))
                            pass
                        elif rt_cd == '0':  # 정상일 경우 처리
                            print("### 체결통보 RETURN CODE [ %s ] MSG [ %s ]" % (rt_cd, jsonObject["body"]["msg1"]))
                            # 체결통보 처리를 위한 AES256 KEY, IV 처리 단계
                            if trid == "K0STCNI0" or trid == "K0STCNI9" or trid == "H0STCNI0" or trid == "H0STCNI9":
                                aes_key = jsonObject["body"]["output"]["key"]
                                aes_iv = jsonObject["body"]["output"]["iv"]
                                print("### TRID [%s] KEY[%s] IV[%s]" % (trid, aes_key, aes_iv))

                    elif trid == "PINGPONG":
                        # print("### RECV [PINGPONG] [%s]" % (data))
                        await websocket.send(data)
                        # print("### SEND [PINGPONG] [%s]" % (data))

    def ExecChecker(self):
        my_loop = asyncio.get_event_loop()
        my_loop.run_until_complete(self.OrderExecWebsocket())
        my_loop.close()


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