import time
import pytesseract
import BeautifulSoup
import re
import requests
from mechanize import Browser
from urllib2 import urlopen
from urlparse import urlparse
import mechanize

from selenium import webdriver

import sys
import argparse
from urllib import urlretrieve
import urlparse
from subprocess import check_output
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

class UrlChange:
    """ URL is checked and a hash is made. Changes are regcognized and
    reported
    """

    def __init__(self, url):
        self.url = url

        self.url_hash = self.create_hash()
        self.content = self.get_content()
        logger.info(("Start Monitoring... hash "
                    "{url_hash}").format(url_hash=self.url_hash))

    def get_content(self):
        """ The data is read from the url. """
        try:
            url_data = urllib.request.urlopen(self.url)
            url_data = url_data.read()
            url_data = url_data.decode("utf-8", "ignore")
            url_data = html2text.html2text(url_data)
        except Exception as e:
            logger.critical("Error: {}".format(e))
            raise
        return url_data

    def create_hash(self):
        """ A md5 hash is created from the url_data. """
        url_data = self.get_content().encode("utf-8")
        md5_hash = hashlib.md5()
        md5_hash.update(url_data)
        return md5_hash.hexdigest()

    def compare_hash(self):
        """ The hash is compared with the stored value. If there is a change
        a function is opend witch alerts the user.
        """
        if(self.create_hash() == self.url_hash):
            logger.info("Nothing has changed")
            return False
        else:
            logger.info("Something has changed")
            date = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            if(not args.nomail):
                send_mail("Url has changed!",
                        ("The Url {url} has changed at "
                        "{date} .").format(url=self.url, date=date))
            if(not args.nodiff):
                diff = self.diff()
                logger.info("{diff}".format(**locals()))
                if(not args.nomail):
                    diff.encode("ascii", "ignore")
                    send_mail("Url difference!",
                            ("The Url {url} has changed at {date} ."
                            "\n\nNew content\n{diff}").format(url=self.url,
                                                                date=date,
                                                                diff=diff))
            return True

    def diff(self):
        """ The function tries to extract the changed part of the url content.
        """
        result = ""
        new_content = self.get_content()
        s = difflib.SequenceMatcher(None, self.content, new_content)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if(tag == "insert" or tag == "replaced"):
                result += new_content[j1:j2]
        return result



# Arguments from the console are parsed
#parser = argparse.ArgumentParser(
                                description=("Monitor ifa website"
                                            "has changed.")
                                )
#parser.add_argument("url", help="url that should be monitored")
#parser.add_argument("-t", "--time",
                    help="seconds between checks (default: 600)",
                    default=600, type=int)
#parser.add_argument("-nd", "--nodiff", help="show no difference",
                    action="store_true")
#parser.add_argument("-n", "--nomail", help="no email is sent",
                    action="store_true")
#args = parser.parse_args()

# A new logging object is created

logging.basicConfig(format="%(asctime)s %(message)s",
                    datefmt="%d.%m.%Y %H:%M:%S")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


url = "http://comprasnet.gov.br/livre/Pregao/Mensagens_Sessao_Publica.asp?prgCod=687204";

#soup = make_soup(url)

#get_images(soup)

#print('Resolving Captcha')

#solver = CaptchaSolver('antigate', api_key='db950dc1814b2f2107523d1ca043dea1')

#raw_data = open('captcha.png', 'rb').read()

#print(solver.solve_captcha(raw_data))

webpage = url # edit me

driver = webdriver.Firefox()

time.sleep(2)

driver.get(webpage)

#sbox = driver.find_element_by_class_name("txtSearch")
image_element = driver.find_element_by_xpath("//img[@src='/scripts/srf/intercepta/captcha.aspx?opt=image']");


location = image_element.location
size = image_element.size

take_screenshot("captcha.png")


crop_image(location, size)

#text = recover_text('captcha.png').strip()

solver = CaptchaSolver('antigate', api_key='db950dc1814b2f2107523d1ca043dea1')

raw_data = open('captcha.png', 'rb').read()

text = solver.solve_captcha(raw_data)

print text

txtbox1 = driver.find_element_by_id('idLetra')
txtbox1.send_keys(text)
time.sleep(5)


#submit
driver.find_element_by_name('Submit').click()

take_screenshot("img{}.jpg".format(%d.%m.%Y))

url1 = UrlChange(args.url)

time.sleep(360)
while(True):
    if(url1.compare_hash()):
        break
    time.sleep(360)
