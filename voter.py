from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

import tkinter, tkinter.messagebox
import time, os, pickle, signal, socket
import config

# Attempts to connect to Google's DNS server
def internet_available() -> bool:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(('8.8.8.8', 53))
            return True
        except socket.error:
            return False

class Voter:
    def loadFirefox(self):
        from selenium.webdriver.firefox.options import Options
        from selenium.webdriver.firefox.service import Service

        if(not os.path.exists(os.curdir + '/.profile')):
            os.mkdir(os.curdir + '/.profile')

        opts = Options()
        opts.add_argument('-profile')
        opts.add_argument(os.curdir + '/.profile')
        if(self.headless):
            opts.add_argument('-headless')
        #opts.binary = "C:/Program Files/Mozilla Firefox/firefox.exe"

        self.driver = webdriver.Firefox(options=opts,
            service=Service(os.curdir + '/geckodriver'))
    
    def loadChrome(self):
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        if(not os.path.exists(os.curdir + '/.userdata')):
            os.mkdir(os.curdir + '/.userdata')
        
        opts = Options()
        opts.add_argument('--user-data-dir=' + os.curdir + '/.userdata')
        opts.add_argument('--disable-extensions')
        if(self.headless):
            opts.add_argument('--headless')

        self.driver = webdriver.Chrome(options=opts,
            service=Service(os.curdir + '/chromedriver'))

    def load(self):
        if(config.browser == "Firefox"):
            self.loadFirefox()
        elif(config.browser == "Chrome"):
            self.loadChrome()
        else:
            print('Unsupported Browser')
            assert False

    def login(self, wait: WebDriverWait):
        # See if we need to actually login
        try:
            wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/form/div/div/div[1]/div[2]/div[1]/div/div[2]/input'))
            # If exception wasn't thrown, then we need to login
            headless = self.headless
            if(headless):
                print('User intervention needed. Leaving headless.')
                self.headless = False
                url = self.driver.current_url
                self.driver.close()
                self.driver.quit()
                self.load()
                self.driver.get(url)
            
            root = tkinter.Tk(screenName='Mudae Auto-Vote')
            tkinter.messagebox.showinfo(title='Mudae Auto-Vote', message='Please login to Discord. DO NOT AUTHORIZE.')
            root.destroy()

            if(headless):
                self.headless = True
                url = self.driver.current_url
                self.driver.close()
                self.driver.quit()
                self.load()
                self.driver.get(url)
                wait = WebDriverWait(self.driver, 10)
        except TimeoutException:
            pass
        
        # Authorize
        auth = wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[1]/div[2]/div/div/div/div/div[2]/button[2]'), "Failed to find Auth button") # Authorize button
        auth.click()

        return

    def vote(self):
        wait = WebDriverWait(self.driver, 10) # Increase if needed

        # Load page
        if(self.driver.current_url == config.bot_link):
            self.driver.refresh()
        else:
            self.driver.get(config.bot_link)
        wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div[2]/div/div[1]/main/div[1]/div/div[2]/button'), "Failed to find Vote button") # find Vote button

        # Login handling
        try:
            lbutton = wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[7]/div[4]/div/section/footer/a[1]/button')) # find Login button
            # If exception wasn't thrown, then we need to login
            lbutton.click()
            self.login(wait)

        except TimeoutException:
            pass

        vote = wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div[2]/div/div[1]/main/div[1]/div/div[2]/button'), "Failed to find Vote button")
        vote.click() # Actually vote

        # Confirm vote
        votetext = wait.until(lambda d: d.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div[2]/div/div[1]/main/div[1]/div/div[1]/div/p[1]'), "Failed to find vote text")
        if(votetext.text == 'Thanks for voting!'):
            print('Voted!')
        elif(votetext.text == 'Something went wrong'):
            if('You have already voted' in self.driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/div[2]/div/div[1]/main/div[1]/div/div[1]/div/p[2]').text):
                print('Vote has already occured.')
                time.sleep(300) # Wait 5 minutes and vote again
                self.vote()
            else:
                print('An error has occured with voting. Trying again.')
                self.vote()
        return

    def run(self):
        while(True):
            try:
                self.load()
                time.sleep(1)
                self.vote()
                time.sleep(1)
                self.driver.close()
                self.driver.quit()
                return
            except WebDriverException:
                if(not internet_available()):
                    # Wait for internet to reconnect and try again
                    while(not internet_available()): 
                        time.sleep(10)
                    pass


class Bot:
    def __init__(self):
        self.bot = Voter()
        self.bot.headless = True

    def run(self):
        if(os.path.exists('lastvote.pkl')):
            lastvote = pickle.load(open('lastvote.pkl', 'rb'))
        else:
            self.bot.run()
            lastvote = time.time()
            pickle.dump(lastvote, open('lastvote.pkl', 'wb'))

        while(True):
            print('Waiting for 12 hours since last vote to elapse.')
            if((time.time() - lastvote) < 43200):
                time.sleep(43200 - (time.time() - lastvote))

            self.bot.run()
            lastvote = time.time()
            pickle.dump(lastvote, open('lastvote.pkl', 'wb'))

    def close(self, signum, frame):
        print('Exiting bot')

        try:
            self.bot.driver.close()
            self.bot.driver.quit()
        except WebDriverException:
            pass

        quit(1)
 

if __name__ == '__main__':
    bot = Bot()
    signal.signal(signal.SIGINT, bot.close)
    bot.run()
