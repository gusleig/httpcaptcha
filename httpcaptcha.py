import time
import pytesseract
import os
import urllib
import requests

from dbhelper import DBHelper

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


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    # text = urllib.urlencode(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    requests.get_url(url)


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

        solver = CaptchaSolver('antigate', api_key='db950dc1814b2f2107523d1ca043dea1')
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

    def __init__(self, web):

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

    def compare_hash(self, bot, db):
        """ The hash is compared with the stored value. If there is a change
        a function is opend witch alerts the user.
        """
        if self.create_hash() == self.url_hash:
            # logger.info("Nothing has changed")
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

            items = db.get_all()

            if len(items) > 0:
                for chat_id in items:
                    bot.send_message(chat_id, "Something has changed")

            print("Url difference!",
                        ("The Url  has changed at {date} ."
                        "\n\nNew content\n{diff}").format(date=date, diff=diff))
        return True


class BotHandler:
    def __init__(self, token):
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)
        self.db = DBHelper()

    def get_updates(self, offset=None, timeout=30):
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_last_update(self):
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[-1]
        else:
            last_update = get_result[len(get_result)]

        return last_update

    def handle_updates(self, updates):
        for update in updates:
            try:

                chat = update["message"]["chat"]["id"]
                name = update["message"]["from"]["last_name"]

                items = self.db.get_items(chat)
                if len(items)>0:
                    if str(chat) not in items:

                        self.db.add_item(name, chat)
                        # items = db.get_items()
                        message = "\n".join(items)
                        # send_message(chat, message)
                else:
                    self.db.add_item(name, chat)

            except KeyError:
                    pass


    def get_last_update_id(self, updates):
        update_ids = []
        for update in updates:
            update_ids.append(int(update["update_id"]))
        return max(update_ids)


__all__ = []


def main():

    db = DBHelper()

    token = "396191661:AAEif0oYT4mgyxPnuztxTaw1DEGyrU4KpSE"

    URL = "https://api.telegram.org/bot{}/".format(token)

    # A new logging object is created

    logging.basicConfig(format="%(asctime)s %(message)s",
                        datefmt="%d.%m.%Y %H:%M:%S")
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    url = "http://comprasnet.gov.br/livre/Pregao/Mensagens_Sessao_Publica.asp?prgCod=687204";

    url = "https://twitter.com/gusleig"

    logger.info("Program init")

    webpage = url # edit me

    driver = webdriver.Firefox()

    time.sleep(2)

    driver.get(webpage)

    # store 1st web page
    url1 = UrlChange2(driver)

    # take_screenshot("screen{}.jpg".format("%d.%m.%Y.%H"))

    time.sleep(6)

    db.setup()
    last_update_id = None
    bot = BotHandler("396191661:AAEif0oYT4mgyxPnuztxTaw1DEGyrU4KpSE")

    while True:

        logger.info("Refreshing page")

        updates = bot.get_updates(last_update_id)

        if len(updates) > 0:
            last_update_id = bot.get_last_update_id(updates) + 1
            bot.handle_updates(updates)

        time.sleep(0.5)

        driver.get(webpage)
        url1.compare_hash(bot, db)
        time.sleep(600)


if __name__ == '__main__':
    main()
