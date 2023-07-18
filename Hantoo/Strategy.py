import traceback
from multiprocessing import *
import configparser
import pprint
import datetime
import json
import quantbox

class Strategy:
    def __init__(self,TotalSubStocks, ExitList, stg_option, Qlist, managerList, account_data):
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

        self.subStocks = TotalSubStocks
        self.ExitList = ExitList
        self.stg_name = stg_option['전략명']
        self.stg_option = stg_option

        self.OpenCutManager = dict()
        self.TodayUniverse = list()

        self.PositionManagerUpdate()
        self.TradingMangerUpdate()
        self.PriceManagerUpadate()
        self.Observer()

    def TradingMangerUpdate(self):
        self.TradingManager.update({x : dict(매수주문여부 = False, 매도주문여부 = False, 매도대상 = False, 매수주문번호 = 0, 매도주문번호 = 0, 매수주문시간 = datetime.datetime.now(), 매도주문시간 = datetime.datetime.now())
                               for x in self.subStocks})

        for stockCode in self.ExitList:
            TradingManager_update = self.TradingManager[stockCode]
            TradingManager_update['매도대상'] = True
            self.TradingManager.update({stockCode : TradingManager_update})

        print('===== Trading Manager Update Done =====')
        pprint.pprint(dict(self.TradingManager))
        print('')

    def PriceManagerUpadate(self):

        config = configparser.ConfigParser()
        config.read('config.ini', encoding='utf-8')

        id = config['퀀트박스']['ID']
        pw = config['퀀트박스']['PW']

        quantbox.set_credentials(id, pw)

        dayopen_id = '8a7b64e55d1b4106ad06fe3d7bd5e0ab'
        dayhigh_id = '90061a7e9c6649348bbf43df106ae4f5'
        daylow_id = 'bd57b20d2b6b40bb8d15e173213f612c'
        dayclose_id = 'c5964cd899fb4ee49ec56eee93f18821'
        dayvolume_id = '5bb1448ad6294e99baa0776057f0f310'

        todate = datetime.datetime.now()
        frdate = datetime.datetime.now() - datetime.timedelta(days = 1)

        frdate = frdate.strftime('%Y%m%d')
        todate = todate.strftime('%Y%m%d')

        dayopen = quantbox.get_wit(dayopen_id, from_date=frdate, to_date=todate, stock_codes=self.subStocks)['result'][dayopen_id]
        dayhigh = quantbox.get_wit(dayhigh_id, from_date=frdate, to_date=todate, stock_codes=self.subStocks)['result'][dayhigh_id]
        daylow = quantbox.get_wit(daylow_id, from_date=frdate, to_date=todate, stock_codes=self.subStocks)['result'][daylow_id]
        dayclose = quantbox.get_wit(dayclose_id, from_date = frdate, to_date = todate, stock_codes=self.subStocks)['result'][dayclose_id]
        dayvolume = quantbox.get_wit(dayvolume_id, from_date=frdate, to_date=todate, stock_codes=self.subStocks)['result'][dayvolume_id]

        print(dayopen)
        print(dayhigh)
        print(daylow)
        print(dayclose)
        print(dayvolume)

        self.PriceManger.update({x : dict(전일시가 = dayopen.iloc[-1][x], 전일고가 = dayhigh.iloc[-1][x], 전일저가 = daylow.iloc[-1][x], 전일종가 = dayclose.iloc[-1][x], 전일거래량 = dayvolume.iloc[-1][x],
                                          당일시가 = 0, 당일고가 = 0, 당일저가 = 0, 현재가 = 0)
                                 for x in self.subStocks})

        self.PriceManger.update({x: dict(전일시가=1, 전일고가=1, 전일저가=1,전일종가=1, 전일거래량=1,당일시가=0, 당일고가=0, 당일저가=0, 현재가=0)for x in self.subStocks})

        print('===== Price Manager Update Done =====')
        pprint.pprint(dict(self.PriceManger))
        print('')

    def PositionManagerUpdate(self):
        self.PositionManager.update({x : dict(평균매수가격 = 0, 보유수량 = 0, 주문번호 = 0, 종목명 = 0, 매수날짜 = None, 매도날짜 = None, 매수예정날짜 = None, 매도예정날짜 = None) for x in self.subStocks})

        try:
            with open(f'log/{self.stg_name}_보유현황.json' ,'r') as file:
                position = json.load(file)
            position = eval(position)

            for stockCode in position.keys():
                if stockCode not in self.PositionManager.keys():
                    self.PositionManager.update({stockCode: dict(종목명=0, 평균매수가격=0, 보유수량=0, 평가금액=0, 평가손익률=0, 평가손익금액=0, 주문번호=0)})

                if position[stockCode]['보유수량'] > 0:
                    PositionManager_update = self.PositionManager[stockCode]
                    PositionManager_update['평균매수가격'] = position[stockCode]['평균매수가격']
                    PositionManager_update['보유수량'] = position[stockCode]['보유수량']
                    PositionManager_update['주문번호'] = position[stockCode]['주문번호']
                    PositionManager_update['종목명'] = position[stockCode]['종목명']
                    PositionManager_update['매수날짜'] = position[stockCode]['매수날짜']
                    PositionManager_update['매도날짜'] = position[stockCode]['매도날짜']
                    PositionManager_update['매수예정날짜'] = position[stockCode]['매수예정날짜']
                    PositionManager_update['매도예정날짜'] = position[stockCode]['매도예정날짜']
                    self.PositionManager.update({stockCode : PositionManager_update})
                    self.BuyList.append(stockCode)
            pprint.pprint(dict(self.PositionManager))
            print(f'보유리스트 >> {self.BuyList}')

        except FileNotFoundError:
            print('아직 매매내역이 없음')
        except:
            print(traceback.format_exc())
            print('오류')

        print('===== Position Manager Update Done =====')
        pprint.pprint(dict(self.PositionManager))

    def Observer(self):
        print('===== Observer Start =====')
        while True:
            now = datetime.datetime.now().strftime('%H%M%S')
            market_start = '090000'
            dongsihoga = '152000'
            market_end = '153000'

            availHoldCnt = self.stg_name['최대보유종목수']

            if self.PriceQ.empty():
                continue

            data = self.PriceQ.get()
            stockCode = data['종목코드']

            PriceManager_update = self.PriceManger[stockCode]

            if now < market_start:  ### 개장전
                if data['TRID'] != 'H0STASP0' or len(self.BalanceManager.keys()) == 0:
                    continue

                expacPrice = abs(float(data['예상체결가']))
                expacQty = abs(float(data['예상체결수량']))

                if self.TradingManager[stockCode]['매수주문여부'] == False and stockCode not in self.BuyList and self.stg_option['매수옵션'] == 'atmarket' and stockCode not in self.ExitList:
                    ### 매수옵션이 atmarket 이고 매수주문을 넣지 않았고 보유종목리스트에 포함되어있지 않고 청산리스트에도 포함되어있지 않으면 시가매수
                    if self.BalanceManager['순자산금액'] < self.BalanceManager['총평가금액'] / len(self.subStocks()):
                        print('[장전 시가매수] 순자산금액이 부족하여 시가매수를 할 수 없음')
                    else:
                        orderQty = (self.BalanceManager['총평가금액'] / availHoldCnt) / expacPrice - 1
                        signalName = '장전시가매수'
                        self.OrderQ.put(('new', stockCode, '매수', 'market', 0, orderQty, signalName))
                        TradingManager_update = self.TradingManager[stockCode]
                        TradingManager_update['매수주문여부'] = True
                        self.TradingManager.update({stockCode : TradingManager_update})
                        print(f'[장전 시가매수] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 주문수량 : {orderQty}')

                elif self.TradingManager[stockCode]["매수주문여부"] == True and stockCode not in self.BuyList and self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys():
                    ### 매수주문을 했으나 예상체결가가 변경되어 매수주문을 수정해야 하는 경우 ###

                    if expacPrice != self.PriceManger[stockCode]['예상체결가'] and self.PriceManger[stockCode]['예상체결가'] != 0: ### 예상체결가격이 변했으면 주문수량을 정정해야 함
                        orderID = self.TradingManager[stockCode]['매수주문번호']
                        orgID = self.OrderManager[orderID]["한국거래소전송주문조직번호"]
                        adj_OrderQty = (self.BalanceManager['총평가금액'] / availHoldCnt) / expacPrice - 1
                        signalName = '장전매수주문수정'
                        side = '매수'
                        self.OrderQ.put(('modify', orgID, orderID, '01', 0, adj_OrderQty, True, signalName, side))  ### '01'은 시장가,
                        print(f'[시가매수 정정] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, {self.OrderManager[orderID]["주문수량"]} >> {adj_OrderQty} 주문수량 수정')

                    elif self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys():
                        orderQty = self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]['주문수량']
                        print(f'[시가매수대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 주문수량 {orderQty}')

                elif stockCode in self.BuyList and self.TradingManager[stockCode]['매도주문여부'] == False and datetime.datetime.now().strftime('%Y%m%d') == self.PositionManager[stockCode]['매도예정날짜'] :  # 보유수량이 있는데 매도주문을 안걸었으면 시가매도
                    ### 보유기간 만기청산
                    signalName = '시가매도 만기청산'
                    self.OrderQ.put((stockCode, '매도', 'market', 0, self.PositionManager[stockCode]["보유수량"], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[시가매도 만기청산] 현재시간 : {datetime.datetime.now().strftime("%Y%m%d")}, 종목코드 : {stockCode}, 매도주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif stockCode in self.ExitList and self.TradingManager[stockCode]['매도주문여부'] == False:
                    signalName = '시가매도 조건부청산'
                    self.OrderQ.put((stockCode, '매도', 'market', 0, self.PositionManager[stockCode]["보유수량"], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[시가매도 조건부청산] 현재시간 : {datetime.datetime.now().strftime("%Y%m%d")}, 종목코드 : {stockCode}, 매도주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif stockCode in self.BuyList and self.TradingManager[stockCode]['매도주문여부'] == True and self.TradingManager[stockCode]['매도주문번호'] in self.OrderManager.keys(): # 보유수량이 있는데 매도주문을 걸었으면 시가매도대기
                    expacProfit = expacPrice / self.PositionManager[stockCode]['평균매수가격'] - 1
                    expacProfit = round(expacProfit * 100, 4)
                    print(f'[시가매도 대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 예상수익률 : {expacProfit}%')
                else:
                    print(f'[개장전] 종목코드 >> {stockCode}, 전일고가 >> {self.PriceManger[stockCode]["전일고가"]}, 전일저가 >> {self.PriceManger[stockCode]["전일저가"]}')

                PriceManager_update['예상체결가'] = expacPrice
                PriceManager_update['예상체결수량'] = expacQty

            elif now > market_start and now < dongsihoga:
                if data['TRID'] != 'H0STCNT0' or len(self.BalanceManager.keys()) == 0:
                    continue

                dayopen = abs(float(data['당일시가']))
                dayhigh = abs(float(data['당일고가']))
                daylow = abs(float(data['당일저가']))
                currentPrice = abs(float(data['현재가']))

                print(f'종목코드 >> {stockCode}, 시가 >> {dayopen}, 고가 >> {dayhigh}, 저가 >> {daylow}, 종가 >> {currentPrice}')

                if self.TradingManager[stockCode]['매수주문여부'] == False and self.stg_option['매수옵션'] == 'atmarket' and stockCode not in self.BuyList and stockCode not in self.ExitList:   ### 시가매수 못했을 때
                    orderQty = (self.BalanceManager['총평가금액']/ len(self.TradingManager.keys())) / currentPrice - 1
                    signalName = '장중신규매수'
                    self.OrderQ.put(('new', stockCode, '매수', 'market', 0, orderQty, signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매수주문여부'] = True
                    print(f'[장중 시가매수] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 주문수량 : {orderQty}')

                elif stockCode not in self.BuyList and self.TradingManager[stockCode]['매수주문여부'] == True and self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys():
                    gap = datetime.datetime.now() - self.TradingManager[stockCode]['매수주문시간']
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

                elif self.TradingManager[stockCode]['매도주문여부'] == False and stockCode in self.ExitList and self.stg_option['매도옵션'] == 'atmarket':
                    signalName = '장중 조건부 매도'
                    self.OrderQ.put(('new', stockCode, '매도', 'market', 0, self.PositionManager[stockCode]['보유수량'], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[장중 조건부 매도] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif self.TradingManager[stockCode]['매도주문여부'] == False and self.PositionManager[stockCode]['매도예정날짜'] == now:
                    signalName = '장중 만기 매도'
                    self.OrderQ.put(('new', stockCode, '매도', 'market', 0, self.PositionManager[stockCode]['보유수량'], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[장중 만기 매도] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif stockCode in self.BuyList and self.TradingManager[stockCode]['매도주문여부'] == True and self.TradingManager[stockCode]['매도주문번호'] in self.OrderManager.keys():
                    gap = datetime.datetime.now() - self.TradingManager[stockCode]['매도주문시간']

                    if self.TradingManager[stockCode]['매도주문번호'] in self.ExecManager.keys():
                        print(f'[매도 미체결] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")},'
                              f' 종목코드 : {stockCode},'
                              f' 미체결시간 : {gap} '
                              f' 주문가격 : {self.OrderManager[self.TradingManager[stockCode]["매도주문번호"]]["주문가격"]},'
                              f' 주문수량 : {self.OrderManager[self.TradingManager[stockCode]["매도주문번호"]]["주문수량"]}'
                              f' 평균매수가격 : {self.ExecManager[self.TradingManager[stockCode]["매도주문번호"]]["평균체결가격"]},'
                              f' 누적체결수량 : {self.ExecManager[self.TradingManager[stockCode]["매도주문번호"]]["누적체결수량"]},'
                              f' 미체결수량 : {self.ExecManager[self.TradingManager[stockCode]["매도주문번호"]]["미체결수량"]}')
                    else:
                        print(f'[매도 미체결 - 하나도 체결안됨] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")},'
                              f' 종목코드 : {stockCode},'
                              f' 미체결시간 : {gap} '
                              f' 주문가격 : {self.OrderManager[self.TradingManager[stockCode]["매도주문번호"]]["주문가격"]},'
                              f' 주문수량 : {self.OrderManager[self.TradingManager[stockCode]["매도주문번호"]]["주문수량"]}')

                elif stockCode in self.BuyList:
                    profit = currentPrice / self.PositionManager[stockCode]["평균매수가격"] - 1
                    profit = round(profit, 4)

                    print(f'[보유중] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, '
                          f'매수날짜 : {self.PositionManager[stockCode]["매수날짜"]} '
                          f'종목코드 : {stockCode}, '
                          f'평균매수가격 : {self.PositionManager[stockCode]["평균매수가격"]}, '
                          f'매수수량 : {self.PositionManager[stockCode]["보유수량"]}, '
                          f'수익률 : {profit}, '
                          f'청산예정일자 : {(self.PositionManager[stockCode]["매도예정날짜"])}')

                PriceManager_update['당일시가'] = dayopen
                PriceManager_update['당일고가'] = dayhigh
                PriceManager_update['당일저가'] = daylow
                PriceManager_update['현재가'] = currentPrice

            elif now > dongsihoga and now < market_end:  ### 3시 20분 동시호가부터 장 마감할떄까지
                if data['TRID'] != 'H0STASP0' or len(self.BalanceManager.keys()) == 0:
                    continue

                expacPrice = abs(float(data['예상체결가']))
                expacQty = abs(float(data['예상체결수량']))

                if self.TradingManager[stockCode]['매수주문여부'] == False and stockCode not in self.BuyList and self.stg_option['매수옵션'] == 'onclose' and stockCode not in self.ExitList:
                    ### 매수옵션이 atmarket 이고 매수주문을 넣지 않았고 보유종목리스트에 포함되어있지 않고 청산리스트에도 포함되어있지 않으면 시가매수
                    if self.BalanceManager['순자산금액'] < self.BalanceManager['총평가금액'] / len(self.subStocks()):
                        print('[동시호가] 순자산금액이 부족하여 종가매수를 할 수 없음')
                    else:
                        orderQty = (self.BalanceManager['총평가금액'] / availHoldCnt) / expacPrice - 1
                        signalName = '종가매수'
                        self.OrderQ.put(('new', stockCode, '매수', 'market', 0, orderQty, signalName))
                        TradingManager_update = self.TradingManager[stockCode]
                        TradingManager_update['매수주문여부'] = True
                        self.TradingManager.update({stockCode : TradingManager_update})
                        print(f'[장마감 종가매수] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 주문수량 : {orderQty}')

                elif self.TradingManager[stockCode]["매수주문여부"] == True and stockCode not in self.BuyList and self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys():
                    ### 매수주문을 했으나 예상체결가가 변경되어 매수주문을 수정해야 하는 경우 ###

                    if expacPrice != self.PriceManger[stockCode]['예상체결가'] and self.PriceManger[stockCode]['예상체결가'] != 0: ### 예상체결가격이 변했으면 주문수량을 정정해야 함
                        orderID = self.TradingManager[stockCode]['매수주문번호']
                        orgID = self.OrderManager[orderID]["한국거래소전송주문조직번호"]
                        adj_OrderQty = (self.BalanceManager['총평가금액'] / availHoldCnt) / expacPrice - 1
                        signalName = '장마감 매수주문수정'
                        side = '매수'
                        self.OrderQ.put(('modify', orgID, orderID, '01', 0, adj_OrderQty, True, signalName, side))  ### '01'은 시장가,
                        print(f'[종가매수 정정] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, {self.OrderManager[orderID]["주문수량"]} >> {adj_OrderQty} 주문수량 수정')

                    elif self.TradingManager[stockCode]['매수주문번호'] in self.OrderManager.keys():
                        orderQty = self.OrderManager[self.TradingManager[stockCode]["매수주문번호"]]['주문수량']
                        print(f'[종가매수대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 주문수량 {orderQty}')

                elif stockCode in self.BuyList and self.TradingManager[stockCode]['매도주문여부'] == False and datetime.datetime.now().strftime('%Y%m%d') == self.PositionManager[stockCode]['매도예정날짜'] :  # 보유수량이 있는데 매도주문을 안걸었으면 시가매도
                    ### 보유기간 만기청산
                    signalName = '종가매도 만기청산'
                    self.OrderQ.put((stockCode, '매도', 'market', 0, self.PositionManager[stockCode]["보유수량"], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[종가매도 만기청산] 현재시간 : {datetime.datetime.now().strftime("%Y%m%d")}, 종목코드 : {stockCode}, 매도주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif stockCode in self.ExitList and self.TradingManager[stockCode]['매도주문여부'] == False:
                    signalName = '종가매도 조건부청산'
                    self.OrderQ.put((stockCode, '매도', 'market', 0, self.PositionManager[stockCode]["보유수량"], signalName))
                    TradingManager_update = self.TradingManager[stockCode]
                    TradingManager_update['매도주문여부'] = True
                    self.TradingManager.update({stockCode: TradingManager_update})
                    print(f'[종가매도 조건부청산] 현재시간 : {datetime.datetime.now().strftime("%Y%m%d")}, 종목코드 : {stockCode}, 매도주문수량 : {self.PositionManager[stockCode]["보유수량"]}')

                elif stockCode in self.BuyList and self.TradingManager[stockCode]['매도주문여부'] == True and self.TradingManager[stockCode]['매도주문번호'] in self.OrderManager.keys(): # 보유수량이 있는데 매도주문을 걸었으면 시가매도대기
                    expacProfit = expacPrice / self.PositionManager[stockCode]['평균매수가격'] - 1
                    expacProfit = round(expacProfit * 100, 4)
                    print(f'[종가매도 대기] 현재시간 : {datetime.datetime.now().strftime("%H:%M:%S")}, 종목코드 : {stockCode}, 예상체결가격 : {expacPrice}, 예상수익률 : {expacProfit}%')
                else:
                    print(f'[동시호가] 종목코드 >> {stockCode}, 예상체결가 >> {expacPrice}, 예상체결수량 >> {expacQty}')

            self.PriceManger.update({stockCode : PriceManager_update})


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

if __name__ == '__main__':

    PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ = \
        Queue(), Queue(), Queue(), Queue(), Queue()

    BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager = \
        Manager().list(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict(), Manager().dict()

    qlist = [PriceQ, OrderQ, OrderCheckQ, ExecCheckQ, WindowQ]
    managerlist = [BuyList, PriceManger, OrderManager, ExecManager, PositionManager, BalanceManager, TradingManager]

    motoo = True
    app_key, secret_key, acc_num, id = get_key(motoo)
    account_data = [app_key, secret_key, acc_num, id, motoo]
    strategy_name = '에러봇'

    subStocks = ['122630','233740']

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

    Strategy(subStocks, stg_option, qlist, managerlist, account_data)




