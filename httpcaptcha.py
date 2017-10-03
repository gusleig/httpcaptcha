import time
import pytesseract
import BeautifulSoup
import re
import os


from urlparse import urlparse

import glob

import sys
import html2text

from urllib import urlretrieve
from urllib2 import urlopen

import urlparse

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

def get_latest_file(path):
    list_of_files = glob.glob('{}\*.png'.format(path))  # * means all if need specific format then *.csv
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file

def get_domain(url):
    parsed_uri = urlparse.urlparse(url)
    domain = '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)
    return domain

def resolve(path):
    print("Resampling the Image")
    check_output(['convert', path, '-resample', '600', path])
    return pytesseract.image_to_string(Image.open(path))

def make_soup(url):
    html = urlopen(url).read()
    return BeautifulSoup.BeautifulSoup(html)

def get_images(soup):

    #this makes a list of bs4 element tags

    images = [img for img in soup.findAll('img')]
    print (str(len(images)) + "images found.")
    print 'Downloading images to current working directory.'
    image_links = [each.get('src') for each in images]
    img = soup.findAll(['img'])
    for i in img:
        try:
            # built the complete URL using the domain and relative url you scraped
            url2 = get_domain(url) + i.get('src')
            # get the file name
            name = "result_" + url2.split('/')[-1]
            name = re.sub('[!@#$=?]', '', name)
            name = "captcha.png"

            # detect if that is a type of pictures you want
            #type = name.split('.')[-1]
            #write picture to disk
            urlretrieve(url2,name)
            #if type in ['jpg', 'png', 'gif']:
                # if so, retrieve the pictures
                #urlretrieve(i.get('src'), name)
        except:
            pass

    return image_links


def create_image(url):
    #br = mechanize.Browser()
    #response = br.open(url)
    #Soup = BeautifulSoup.BeautifulSoup(response.get_data())
    #Solver = CaptchaSolver('browser')
    get_images(url)
    #image_response = br.open_novisit(img['src'])
    #image = image_response.read()

    return image


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
            if tag == "insert" or tag == "replaced":
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
            logger.info("Something has changed")
            date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            diff = self.diff()

            logger.info("{diff}".format(**locals()))

            diff.encode("ascii", "ignore")

            # reset
            self.url_hash = self.create_hash()
            self.content = self.get_content()

            print("Url difference!",
                        ("The Url  has changed at {date} ."
                        "\n\nNew content\n{diff}").format(date=date, diff=diff))
        return True


root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# A new logging object is created

logging.basicConfig(format="%(asctime)s %(message)s",
                    datefmt="%d.%m.%Y %H:%M:%S")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


url = "http://comprasnet.gov.br/livre/Pregao/Mensagens_Sessao_Publica.asp?prgCod=687204";

# url = "https://twitter.com/gusleig"
# latest_print= get_latest_file(os.path.dirname(os.path.realpath(__file__)))
#soup = make_soup(url)
#get_images(soup)
#print('Resolving Captcha')
#solver = CaptchaSolver('antigate', api_key='db950dc1814b2f2107523d1ca043dea1')
#raw_data = open('captcha.png', 'rb').read()
#print(solver.solve_captcha(raw_data))

logger.info("Program init")

webpage = url # edit me

driver = webdriver.Firefox()

time.sleep(2)

driver.get(webpage)

# store 1st web page
url1 = UrlChange2(driver)

# take_screenshot("screen{}.jpg".format("%d.%m.%Y.%H"))

time.sleep(6)

while True:
    logger.info("Refreshing page")
    driver.get(webpage)
    url1.compare_hash()
    time.sleep(600)