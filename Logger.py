import telepot
import logging
import configparser

class Logger:
    def __init__(self):

        self.config = configparser.ConfigParser()
        self.config.read('../ignore/config.ini', encoding = 'utf-8')

    def telegram_bot(self, channel_name, msg):
        bot_token = self.config['tele_bot']['token']
        channel_id = self.config['tele_bot'][channel_name]
        bot = telepot.Bot(token=bot_token)
        bot.sendMessage(chat_id=channel_id, text=msg)

    def CreateLogger(self, method):
        logger = logging.getLogger(method)

        if len(logger.handlers) > 0:
            return logger
        logger.setLevel(logging.INFO)

        if method == 'error':
            log_path = 'log/error.txt'
            filehandler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter('\n%(asctime)s\n%(message)s')
        else:
            log_path = f'log/{method}.txt'
            filehandler = logging.FileHandler(log_path, encoding="utf-8")
            formatter = logging.Formatter('%(message)s')
        filehandler.setFormatter(formatter)
        logger.addHandler(filehandler)
        return logger

    def add_log(self, msg, method = None):
        logger = self.CreateLogger(method)
        if method == 'error':
            logger.exception(msg)
        else:
            logger.info(msg)

if __name__ == '__main__':
    log = Logger()
    stg_name = '직장인투자전략'

    log.telegram_bot(stg_name, 'error')