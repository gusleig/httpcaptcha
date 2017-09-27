import os
import requests
import json
import sys
import time
import telepot
import shelve
import logging
import traceback

from PIL import Image
import ImageEnhance
from pytesser import *
from urllib import urlretrieve

TELEGRAM_TOKEN="396191661:AAEif0oYT4mgyxPnuztxTaw1DEGyrU4KpSE"

DB_FILE = 'data/bot.shelve.db'
EXCHANGES = {
    'poloniex': {
        'name': 'Poloniex',
        'url': 'https://www.poloniex.com/exchange#{}',
        'lowercase': True
    },
    'bittrex': {
        'name': 'Bittrex',
        'url': 'https://bittrex.com/Market/Index?MarketName={}'
    },
    'liqui.io': {
        'name': 'Liqui.io',
        'url': 'https://liqui.io/#/exchange/{}',
        'uppercase': True
    },
    'tidex': {
        'name': 'Tidex',
        'url': 'https://tidex.com/exchange/#/pair/{}',
        'uppercase': True
    }
}


def get(link):
    urlretrieve(link, 'temp.png')


get('http://comprasnet.gov.br/livre/Pregao/Mensagens_Sessao_Publica.asp?prgCod=687204');
im = Image.open("temp.png")
nx, ny = im.size
im2 = im.resize((int(nx * 5), int(ny * 5)), Image.BICUBIC)
im2.save("temp2.png")
enh = ImageEnhance.Contrast(im)
enh.enhance(1.3).show("30% more contrast")

imgx = Image.open('temp2.png')
imgx = imgx.convert("RGBA")
pix = imgx.load()
for y in xrange(imgx.size[1]):
    for x in xrange(imgx.size[0]):
        if pix[x, y] != (0, 0, 0, 255):
            pix[x, y] = (255, 255, 255, 255)
imgx.save("bw.gif", "GIF")
original = Image.open('bw.gif')
bg = original.resize((116, 56), Image.NEAREST)
ext = ".tif"
bg.save("input-NEAREST" + ext)
image = Image.open('input-NEAREST.tif')
print image_to_string(image)