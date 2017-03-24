import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import *
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
import argparse
import random
import sys

parser = argparse.ArgumentParser(description='Selenium script to view account details and perform a search in AltoroJ 3.0')
parser.add_argument("-m", "--manualexporeserver", action="store", help="Manual Explore Server host name  e.g. appscanvm")
parser.add_argument("-p", "--proxyport", action="store", help="Manual Explore Listening Port e.g. 19555")
args = parser.parse_args()
delay = 90

#Create the Firefox profile so we can change the proxy
prof = webdriver.FirefoxProfile()
prof.update_preferences()
fp = webdriver.FirefoxProfile()

if(args.manualexporeserver is not None):
    #Proxy Type: Direct = 0, Manual = 1, PAC = 2, AUTODETECT = 4, SYSTEM = 5
    PROXY_HOST = args.manualexporeserver
    PROXY_PORT = args.proxyport
    PROXY_TYPE = 1
    fp.set_preference("network.proxy.type", PROXY_TYPE)
    fp.set_preference("network.proxy.http",PROXY_HOST)
    fp.set_preference("network.proxy.http_port",int(PROXY_PORT))
    fp.update_preferences()

#Set the proxy in the profile and update the driver
browser = webdriver.Firefox(firefox_profile=fp)

#Go to main url
browser.get('http://appscanvm:8088/AltoroJ/')

try:
    WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, 'LoginLink')))
except TimeoutException:
    sys.exit("Selenium Script Timed Out. Exiting")
    
#Click on sign in
browser.find_element_by_id('LoginLink').click()
time.sleep(10)

try:
    WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.NAME, 'btnSubmit')))
except TimeoutException:
    sys.exit("Selenium Script Timed Out. Exiting")

#Provide sign in credentials
browser.find_element_by_name('uid').send_keys('jsmith')
browser.find_element_by_name('passw').send_keys('demo1234')
browser.find_element_by_name('btnSubmit').click()

try:
    WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, 'btnGetAccount')))
except TimeoutException:
    sys.exit("Selenium Script Timed Out. Exiting")

#View details of the first account
browser.find_element_by_id('btnGetAccount').click()

try:
    WebDriverWait(browser, delay).until(EC.presence_of_element_located((By.ID, 'query')))
except TimeoutException:
    sys.exit("Selenium Script Timed Out. Exiting")

#Search some stuff
#browser.find_element_by_id('query').send_keys('Test search' + Keys.RETURN)
time.sleep(3)

#Close the Browser
browser.quit()
time.sleep(3)
