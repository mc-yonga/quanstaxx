import websockets
import json
import asyncio
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
from multiprocessing import *
from Logger import *
import traceback

clearConsole = lambda: os.system('cls' if os.name in ('nt', 'dos') else 'clear')

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

def stockhoka(data):
    recvvalue = data.split('^')  # 수신데이터를 split '^'
    return dict(종목코드 = recvvalue[0], 예상체결가 = int(recvvalue[47]), 예상체결수량 = int(recvvalue[48]), 예상거래량 = int(recvvalue[49]), 매수호가01 = int(recvvalue[13]), 매수호가01잔량 = int(recvvalue[33]), 매도호가01 = int(recvvalue[3]), 매도호가01잔량 = int(recvvalue[23]), TRID = 'H0STASP0')

def stocks_purchase(data):
    menulist = "유가증권단축종목코드|주식체결시간|주식현재가|전일대비부호|전일대비|전일대비율|가중평균주식가격|주식시가|주식최고가|주식최저가|매도호가1|매수호가1|체결거래량|누적거래량|누적거래대금|매도체결건수|매수체결건수|순매수체결건수|체결강도|총매도수량|총매수수량|체결구분|매수비율|전일거래량대비등락율|시가시간|시가대비구분|시가대비|최고가시간|고가대비구분|고가대비|최저가시간|저가대비구분|저가대비|영업일자|신장운영구분코드|거래정지여부|매도호가잔량|매수호가잔량|총매도호가잔량|총매수호가잔량|거래량회전율|전일동시간누적거래량|전일동시간누적거래량비율|시간구분코드|임의종료구분코드|정적VI발동기준가"
    menustr = menulist.split('|')
    pValue = data.split('^')
    data_list = {}
    for i in range(len(menustr)):     # 넘겨받은 체결데이터 개수만큼 print 한다
        data_list.update({menustr[i] : pValue[i]})
    return data_list

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
        Logger().add_log('', 'error')
        Logger().telegram_bot('에러봇', '복호화 과정에서 에러발생')

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

class Receiver:
    def __init__(self,TotalSubStocks, stg_option, Qlist, managerList, account_data):

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
        self.subsStocks = TotalSubStocks

        # self.stg_name = stg_option['전략명']
        self.logger = Logger()
        self.PriceExecChecker()

    async def PriceExecWebsocket(self):

        if self.motoo == True:
            url = 'ws://ops.koreainvestment.com:31000'  # 모의계좌
            tr_id = 'H0STCNI9'
        else:
            url = 'ws://ops.koreainvestment.com:21000'  # 실전계좌
            tr_id = 'H0STCNI0'

        approval_key = get_approval(self.app_key, self.secret_key)

        code_list = [['1', 'H0STCNT0', x] for x in self.subsStocks]
        code_list2 = [['1', 'H0STASP0', x] for x in self.subsStocks]

        send_data_list = []
        for i, j, k in code_list:
            temp = '{"header":{"approval_key": "%s","custtype":"%s","tr_type":"%s","content-type":"utf-8"},"body":{"input":{"tr_id":"%s","tr_key":"%s"}}}' % (approval_key, 'P', i, j, k)
            send_data_list.append(temp)

        for i, j, k in code_list2:
            temp = '{"header":{"approval_key": "%s","custtype":"%s","tr_type":"%s","content-type":"utf-8"},"body":{"input":{"tr_id":"%s","tr_key":"%s"}}}' % (approval_key, 'P', i, j, k)
            send_data_list.append(temp)

        code_list = ['1', tr_id, self.id]
        temp = '{"header":{"approval_key": "%s","custtype":"P","tr_type":"%s","content-type":"utf-8"},"body":{"input":{"tr_id":"%s","tr_key":"%s"}}}' % (
            approval_key, code_list[0], code_list[1], code_list[2])
        send_data_list.append(temp)

        async with websockets.connect(url, ping_interval = None) as websocket:
            for send_data in send_data_list:
                await websocket.send(send_data)

            print('\n======================== Receiver Start ========================\n')

            while True:
                if not websocket.open:
                    try:
                        websocket = await websocket.connect(url)
                        for send_data in send_data_list:
                            await websocket.send(send_data)
                    except:
                        print('웹소켓 재연결 시도중 ...')

                data = await websocket.recv()

                if data[0] == '0':
                    recvstr = data.split('|')
                    trid0 = recvstr[1]

                    if trid0 == 'H0STASP0':
                        result = stockhoka(recvstr[3])
                        self.PriceQ.put(result)

                    elif trid0 == 'H0STCNT0':
                        resp = stocks_purchase(recvstr[3])
                        stock_code = resp['유가증권단축종목코드']
                        dayopen = int(resp['주식시가'])
                        dayhigh = int(resp['주식최고가'])
                        daylow = int(resp['주식최저가'])
                        dayclose = int(resp['주식현재가'])
                        dayvolume = int(resp['누적거래량'])
                        dayamount = int(resp['누적거래대금'])
                        buy_hoka1 = int(resp['매수호가1'])
                        sell_hoka1 = int(resp['매도호가1'])

                        result = dict(종목코드 = stock_code, 당일시가 = dayopen, 당일고가 = dayhigh, 당일저가 = daylow, 현재가 = dayclose,
                                  당일누적거래량 = dayvolume, 당일누적거래대금 = dayamount, 매수호가1 = buy_hoka1, 매도호가1 = sell_hoka1, TRID = 'H0STCNT0')

                        self.PriceQ.put(result)

                elif data[0] == '1':
                    recvstr = data.split('|')  # 수신데이터가 실데이터 이전은 '|'로 나뉘어져있어 split
                    trid0 = recvstr[1]
                    if trid0 == "K0STCNI0" or trid0 == "K0STCNI9" or trid0 == "H0STCNI0" or trid0 == "H0STCNI9":
                        resp = OrderExecData(recvstr[3], aes_key, aes_iv)
                        self.ExecQ.put(resp)

                else:
                    jsonObject = json.loads(data)
                    trid = jsonObject["header"]["tr_id"]

                    if trid != "PINGPONG":
                        rt_cd = jsonObject["body"]["rt_cd"]
                        if rt_cd == '1':  # 에러일 경우 처리
                            print("### 현재가 ERROR RETURN CODE [ %s ] MSG [ %s ]" % (rt_cd, jsonObject["body"]["msg1"]))
                            pass
                        elif rt_cd == '0':  # 정상일 경우 처리
                            print("### 현재가 RETURN CODE [ %s ] MSG [ %s ]" % (rt_cd, jsonObject["body"]["msg1"]))
                            # 체결통보 처리를 위한 AES256 KEY, IV 처리 단계
                            if trid == "K0STCNI0" or trid == "K0STCNI9" or trid == "H0STCNI0" or trid == "H0STCNI9":
                                aes_key = jsonObject["body"]["output"]["key"]
                                aes_iv = jsonObject["body"]["output"]["iv"]
                                print("### TRID [%s] KEY[%s] IV[%s]" % (trid, aes_key, aes_iv))

                    elif trid == "PINGPONG":
                        print("### RECV [PINGPONG] [%s]" % (data))
                        await websocket.send(data)
                        print("### SEND [PINGPONG] [%s]" % (data))

    def PriceExecChecker(self):
        my_loop = asyncio.get_event_loop()
        my_loop.run_until_complete(self.PriceExecWebsocket())
        my_loop.close()

if __name__ == '__main__':
    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    motoo = True
    app_key, secret_key, acc_num, id = get_key(motoo)
    print(app_key)
    print(secret_key)
    account_data = [app_key, secret_key, acc_num, id, motoo]
    strategy_name = '테스트'

    subStocks = ['122630', '233740']
    stg_option = None
    Receiver(subStocks, stg_option, qlist, managerlist, account_data)

