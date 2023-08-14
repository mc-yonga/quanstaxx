import configparser
import pickle
import mojito
import requests
import json

def get_key():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')

    app_key = config['투자전략기본']['한투앱키']
    secret_key = config['투자전략기본']['한투시크릿']
    acc_num = config['투자전략기본']['한투계좌번호']
    id = config['투자전략기본']['한투아이디']

    return app_key, secret_key, acc_num, id

class Token:
    def __init__(self, motoo):
        """

        :param motoo: True or False
                """

        app_key, secret_key, acc_num, id = get_key()
        self.app_key = app_key
        self.secret_key = secret_key
        self.acc_num = acc_num
        self.id = id

        if motoo == False:
            self.base_url = 'https://openapi.koreainvestment.com:9443'
        else:
            self.base_url = 'https://openapivts.koreainvestment.com:29443'
        self.config = configparser.ConfigParser()
        self.config.read('config.ini', encoding = 'utf-8')

        try:
            with open("token.dat", "rb") as f:
                data = pickle.load(f)
                self.access_token = f'Bearer {data["access_token"]}'
        except:
            self.get_access_token()

        self.broker = mojito.KoreaInvestment(
            api_key = self.app_key,
            api_secret = self.secret_key,
            acc_no = self.acc_num,
            mock = motoo
            )

    def get_access_token(self):
        headers = {"content-type": "application/json"}
        body = {"grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.secret_key}
        PATH = "oauth2/tokenP"
        URL = f"{self.base_url}/{PATH}"
        res = requests.post(URL, headers=headers, data=json.dumps(body))
        ACCESS_TOKEN = res.json()["access_token"]
        # print('토큰갱신완료')
        return ACCESS_TOKEN

if __name__ == '__main__':
    stg_name = '모의투자'
    Token(stg_name).get_access_token()