import numpy as np
import math

def etf_up_price(price):  # 올림 가격을 구해줍니다. (2131원 => 2135원)
    if np.isnan(price):
        return np.nan
    hogaPrice = math.ceil(price)  # 소수점은 올려준다.
    hoga = 5
    while hogaPrice % hoga != 0:
        hogaPrice = hogaPrice + 1
    return hogaPrice

def etf_down_price(price):  # 내림 가격을 구해줍니다. (2131원 => 2130원)
    if np.isnan(price):
        return np.nan
    hogaPrice = math.floor(price)
    hoga = 5
    while hogaPrice % hoga != 0:
        hogaPrice = hogaPrice - 1
    return hogaPrice
