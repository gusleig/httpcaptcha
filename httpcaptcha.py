import time
import os
import urllib
import requests
import telepot
import shelve
import configparser



try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import glob

import sys
import html2text

from captcha_solver import CaptchaSolver
from selenium import webdriver

import datetime
import difflib
import hashlib
import html2text
import logging

try:
    import Image
except ImportError:
    from PIL import Image

from subprocess import check_output


class ReadConfig:
    def __init__(self):
        self.setup = self.setup_config()
        self.apikey = self.get_api()

    def setup_config(self):

        Config.read("config.ini")
        try:
            cfgfile = open("config.ini", 'r')
        except:
            logger.info("Creating config file")
            cfgfile = open("config.ini", 'w')
            Config.add_section('config')
            Config.set('config', 'apikey', "")
            Config.write(cfgfile)
            cfgfile.close()
            Config.read("config.ini")
        return True

    def get_api(self):

        try:
            self.apikey = Config.get("config", "apikey")
        except:
            logger.info("Creating apikey option")
            Config.set("config", "apikey", "")
        return self.apikey


def get_latest_file(path):
    list_of_files = glob.glob('{}\*.png'.format(path))  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def get_domain(url):
    parsed_uri = urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    return domain


def resolve(path):
    print("Resampling the Image")
    check_output(['convert', path, '-resample', '600', path])
    return pytesseract.image_to_string(Image.open(path))


def get_session_id(raw_resp):
    soup = bs(raw_resp.text, 'lxml')
    token = soup.find_all('input', {'name':'survey_session_id'})[0]['value']
    return token


def take_screenshot(name):
    driver.save_screenshot(name)


def crop_image(location, size):
    image = Image.open('captcha.png')
    x, y = location['x'], location['y']
    w, h = size['width'], size['height']
    image.crop((x, y, x + w, y + h)).save('captcha.png')


def recover_text(filename):
    image = Image.open('captcha.png')
    r, g, b, a = image.split()  # removing the alpha channel
    image = Image.merge('RGB', (r, g, b))
    return pytesseract.image_to_string(image)


def has_captcha(web):
    exist = False
    try:
        element = web.find_element_by_xpath("//img[@src='/scripts/srf/intercepta/captcha.aspx?opt=image']");
        exist = True
    except Exception as e:
        return exist
    return exist


def bypass_captcha(web):
    # bypass captcha
    logger.info("Bypassing captcha")
    x = 0

    apikey = settings.apikey

    while True:
        try:
            image_element = web.find_element_by_xpath("//img[@src='/scripts/srf/intercepta/captcha.aspx?opt=image']");
        except Exception:
            logger.info("Web server error: captcha not located")
            return False

        location = image_element.location
        size = image_element.size

        take_screenshot("captcha.png")
        crop_image(location, size)

        solver = CaptchaSolver('antigate', api_key=apikey)

        raw_data = open('captcha.png', 'rb').read()

        text = solver.solve_captcha(raw_data)
        try:
            txtbox1 = web.find_element_by_id('idLetra')
            txtbox1.send_keys(text)
        except Exception:
            logger.info("Web server error")
            return False

        time.sleep(2)
        # submit
        web.find_element_by_name('Submit').click()

        time.sleep(5)

        try:
            # if captcha still there, need to try again
            image_element = web.find_element_by_xpath("//img[@src='/scripts/srf/intercepta/captcha.aspx?opt=image']")

            logger.info("captcha error")
            x += 1
            if x > 3:
                return False
        except Exception:
            return True


class UrlChange2:

    def __init__(self, bot, web):

        self.bot = bot
        self.web = web
        if has_captcha(web):
            bypass_captcha(web)
        self.url_hash = self.create_hash()
        self.content = self.get_content()

    def get_content(self):
        try:
            url_data = self.web.page_source
            # url_data = url_data.decode("utf-8", "ignore")
            url_data = html2text.html2text(url_data)
        except Exception as e:
            logger.critical("Error: {}".format(e))
            raise
        return url_data

    def create_hash(self):

        if has_captcha(self.web):
            bypass_captcha(self.web)
        url_data = self.web.page_source.encode("utf-8")
        md5_hash = hashlib.md5()
        md5_hash.update(url_data)
        return md5_hash.hexdigest()

    def diff(self):
        """ The function tries to extract the changed part of the url content.
        """
        result = ""
        new_content = self.get_content()
        s = difflib.SequenceMatcher(None, self.content, new_content)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == "insert" or tag == "replaced" or tag == "replace":
                result += new_content[j1:j2]
        return result

    def compare_hash(self):
        """ The hash is compared with the stored value. If there is a change
        a function is opend witch alerts the user.
        """
        if self.create_hash() == self.url_hash:
            logger.info("Nothing has changed")
            return False
        else:

            # logger.info("Something has changed")
            date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            diff = self.diff()

            # logger.info("{diff}".format(**locals()))

            diff.encode("ascii", "ignore")

            # reset
            self.url_hash = self.create_hash()
            self.content = self.get_content()

            # items = db.get_all()
            self.bot.notify_post("Changed at {date}.\n{diff}".format(date=date, diff=diff))

            print("Url difference!",
                        ("The Url  has changed at {date} ."
                        "\n\nNew content\n{diff}").format(date=date, diff=diff))
        return True


class Bot:
    def __init__(self, token):
        # self.token = token
        # self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.bot = telepot.Bot(token)
        self.me = self.bot.getMe()
        self.bot.message_loop(self._on_message)
        self.db = shelve.open(DB_FILE)

        # self.db = DBHelper()

    def _on_message(self, msg):
        user_id = msg['from']['id']
        self.db[str(user_id)] = msg['from']

        self.db.sync()

        command = msg['text'].split(' ')
        if len(command) > 0 and (command[0] == '/help' or command[0] == 'Help'):
            text = """You can use the following commands:
/url - List out all url being tracked
/debug - Internal info for nerds
            """
            self.bot.sendMessage(user_id, text, reply_markup=DEFAULT_REPLY_MARKUP)
            return

    def notify_post(self, post):
        # text = 'New potential changes on r/{}:\n\n{}'.format(forum,  'https://reddit.com{}'.format(post['permalink'].encode('utf-8')))
        text = "New changes.{text}".format(text=post)

        for user_id in self.db:
            logging.info('Sending rumor notification to {}'.format(user_id))
            try:
                self.bot.sendMessage(user_id, text, reply_markup=DEFAULT_REPLY_MARKUP)
                time.sleep(1)
            except telepot.exception.BotWasBlockedError:
                logging.info('User {} blocked the bot, skipping'.format(user_id))
            except:
                logging.info('Unknown error sending to user {}, skipping'.format(user_id))




__all__ = []


DB_FILE = 'data/bot.shelve.db'

DEFAULT_REPLY_MARKUP = {'keyboard': [['Check', 'Help']], 'resize_keyboard': True}

token = "396191661:AAEif0oYT4mgyxPnuztxTaw1DEGyrU4KpSE"

# A new logging object is created

logging.basicConfig(format="%(asctime)s %(message)s",
                    datefmt="%d.%m.%Y %H:%M:%S")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

driver = webdriver.Firefox()

# Read config.ini
Config = configparser.ConfigParser()

settings = ReadConfig()

if settings.apikey == "":
    logger.info("Missing apikey in config.ini")
    exit()


def main():

    # db = DBHelper()
    bot = Bot("396191661:AAEif0oYT4mgyxPnuztxTaw1DEGyrU4KpSE")

    url = "http://comprasnet.gov.br/livre/Pregao/Mensagens_Sessao_Publica.asp?prgCod=687204";

    # url = "https://twitter.com/gusleig"

    logger.info("Program init")

    webpage = url # edit me

    time.sleep(2)

    driver.get(webpage)

    # store 1st web page
    url1 = UrlChange2(bot, driver)

    # take_screenshot("screen{}.jpg".format("%d.%m.%Y.%H"))

    time.sleep(6)

    while True:

        logger.info("Refreshing page")

        time.sleep(0.5)

        driver.get(webpage)
        url1.compare_hash()
        time.sleep(600)


if __name__ == '__main__':
    main()
