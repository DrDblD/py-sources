import requests
from bs4 import BeautifulSoup
import urllib.parse

api_url = 'https://logs2.poidem.ru/api'

def get_swagger(url):
    next_url = urllib.parse.urljoin(url, "api-browser")
    rq = requests.get(next_url)
    print(rq)