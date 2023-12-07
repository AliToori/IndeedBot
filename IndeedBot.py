#!/usr/bin/env python3
"""
    *******************************************************************************************
    IndeedBot.
    Author: Ali Toori, Python Developer
    *******************************************************************************************
"""
import json
import logging.config
import os
import pickle
import random
from datetime import datetime
from multiprocessing import freeze_support
from pathlib import Path
from time import sleep
import concurrent.futures
import re
import pandas as pd
import pyfiglet
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class IndeedBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.file_settings = str(self.PROJECT_ROOT / 'IndeedRes/Settings.json')
        self.file_cities = self.PROJECT_ROOT / 'IndeedRes/Cities.csv'
        self.INDEED_HOME_URL = "https://ca.indeed.com/jobs?l="
        self.settings = self.get_settings()
        self.LOGGER = self.get_logger()
        self.driver = None

    # Get self.LOGGER
    @staticmethod
    def get_logger():
        """
        Get logger file handler
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '%(asctime)s,%(lineno)s] [%(message)s',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "filename": "IndeedBot.log",
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 1
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    @staticmethod
    def enable_cmd_colors():
        # Enables Windows New ANSI Support for Colored Printing on CMD
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ IndeedBot\n', colors='RED')
        print('Author: Ali Toori\n'
              'Website: https://instagram.com/botflocks/\n'
              '************************************************************************')

    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "ThreadsCount": 5
        }}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # Get random user-agent
    def get_user_agent(self):
        file_uagents = self.PROJECT_ROOT / 'IndeedRes/user_agents.txt'
        with open(file_uagents) as f:
            content = f.readlines()
        u_agents_list = [x.strip() for x in content]
        return random.choice(u_agents_list)

    # Get random user-agent
    def get_proxy(self):
        file_proxies = self.PROJECT_ROOT / 'IndeedRes/proxies.txt'
        with open(file_proxies) as f:
            content = f.readlines()
        proxy_list = [x.strip() for x in content]
        return random.choice(proxy_list)

    # Get web driver
    def get_driver(self, proxy=False, headless=False):
        # For absolute chromedriver path
        DRIVER_BIN = str(self.PROJECT_ROOT / "IndeedRes/bin/chromedriver.exe")
        service = Service(executable_path=DRIVER_BIN)
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features")
        options.add_argument('--ignore-ssl-errors')
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(F'--user-agent={self.get_user_agent()}')
        # options.add_argument('--headless')
        if proxy:
            options.add_argument(f"--proxy-server={self.get_proxy()}")
        if headless:
            options.add_argument('--headless')
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    # Finish and quit browser
    def finish(self, driver):
        try:
            self.LOGGER.info(f'Closing browser')
            driver.close()
            driver.quit()
        except WebDriverException as exc:
            self.LOGGER.info(f'Issue while closing browser: {exc.args}')

    @staticmethod
    def wait_until_visible(driver, css_selector=None, element_id=None, name=None, class_name=None, tag_name=None, duration=10000, frequency=0.01):
        if css_selector:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
        elif element_id:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.ID, element_id)))
        elif name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.NAME, name)))
        elif class_name:
            WebDriverWait(driver, duration, frequency).until(
                EC.visibility_of_element_located((By.CLASS_NAME, class_name)))
        elif tag_name:
            WebDriverWait(driver, duration, frequency).until(EC.visibility_of_element_located((By.TAG_NAME, tag_name)))

    def get_job_posts(self, city):
        file_city = self.PROJECT_ROOT / f'IndeedRes/{city}.csv'
        driver = self.get_driver()
        print('Scraping Indeed Jobs in ')
        self.LOGGER.info(f"City: {str(city)}")
        # url_final = 'https://www.indeed.com/jobs?q=' + title + '&l=' + state_name + '&jt=' + type
        url_final = f"https://ca.indeed.com/jobs?q=&l={city}&start=0"
        self.LOGGER.info(f"Requesting: {str(url_final)}")
        driver.get(url_final)
        self.LOGGER.info("Waiting for the search results to become visible")
        self.wait_until_visible(driver, css_selector='[class="jobsearch-ResultsList css-0"]', duration=30)
        self.LOGGER.info("Search results has been visible")
        # driver.find_element_by_tag_name('html').send_keys(Keys.SPACE)
        number_of_pages = 5
        actions = ActionChains(driver)
        try:
            self.LOGGER.info("Waiting for page count")
            self.wait_until_visible(driver, css_selector='[class="jobsearch-JobCountAndSortPane-jobCount"]', duration=10)
            total_jobs = str(driver.find_element(By.CSS_SELECTOR, '[class="jobsearch-JobCountAndSortPane-jobCount"]').text).replace(',', '').replace('Page 1 of', '').replace('jobs', '')
            total_jobs = re.findall(pattern=r'\d+', string=total_jobs)
            # print(f'Total jobs re list: {total_jobs}')
            total_jobs = total_jobs[0]
            self.LOGGER.info(f"Total Jobs: {total_jobs}")
            number_of_pages = round(int(total_jobs) / 10)
            self.LOGGER.info(f"Number of pages: {number_of_pages}")
        except:
            try:
                self.LOGGER.info("Waiting 2nd time for page count")
                self.wait_until_visible(driver, css_selector='[id="searchCountPages"]', duration=5)
                total_jobs = str(driver.find_element(By.CSS_SELECTOR, '[id="searchCountPages"]').text).replace(',', '').replace('Page 1 of', '').replace('jobs', '')
                total_jobs = re.findall(pattern=r'\d+', string=total_jobs)
                total_jobs = total_jobs[0]
                self.LOGGER.info(f"Total Jobs: {total_jobs}")
                number_of_pages = round(int(total_jobs) / 10)
                self.LOGGER.info(f"Number of pages: {number_of_pages}")
            except:
                number_of_pages = 25
        job_count = 1510
        pages_scraped = 151
        jobs_scraped = pages_scraped * 15
        for page in range(pages_scraped, number_of_pages):
            page_url = f"https://ca.indeed.com/jobs?q=&l={city}&start={job_count}"
            driver.get(page_url)
            sleep(3)
            self.LOGGER.info(f"Pages Scraped {pages_scraped} of {number_of_pages}")
            self.LOGGER.info(f"Job posts scraped {jobs_scraped} of {total_jobs}")
            job_count += 10
            pages_scraped += 1
            jobs_scraped += 15
            job_title, company_name, location, salary, job_type, date_posted, contact, reviews, job_url, listing_url = '', '', '', '', '', '', '', '', '', ''
            self.wait_until_visible(driver, css_selector='[class="jobsearch-ResultsList css-0"]', duration=30)
            for i, jobs in enumerate(driver.find_element(By.CSS_SELECTOR, '[class="jobsearch-ResultsList css-0"]').find_elements(By.CSS_SELECTOR, '[class="job_seen_beacon"]')):
                # jobs_in_page = len(driver.find_element(By.CSS_SELECTOR, '[class="jobsearch-ResultsList css-0"]').find_elements(By.CSS_SELECTOR, '[class="job_seen_beacon"]'))
                # print(f'JOBS IN THE LIST:{jobs_in_page}')
                job = driver.find_element(By.CSS_SELECTOR, '[class="jobsearch-ResultsList css-0"]').find_elements(By.CSS_SELECTOR, '[class="job_seen_beacon"]')[i]
                # Scroll element into view
                driver.execute_script("arguments[0].scrollIntoView();", job)
                sleep(1)
                self.LOGGER.info(f"Selecting Job {i + 1}")
                try:
                    actions.move_to_element(job)
                    actions.click(job).perform()
                except:
                    try:
                        job_card = job.find_element(By.CSS_SELECTOR, '[class="job_seen_beacon"]')
                        actions.move_to_element(job_card)
                        actions.click(job_card).perform()
                    except:
                        pass
                try:
                    job.click()
                except:
                    try:
                        job.find_element(By.CSS_SELECTOR, '[class="job_seen_beacon"]').click()
                    except:
                        pass
                self.LOGGER.info("Job has been selected")
                # Get ListingURL, JobTitle, CompanyName and JobURL from the left side listing
                try:
                    job_title = driver.find_elements(By.CSS_SELECTOR, '[class="jcs-JobTitle css-jspxzf eu4oa1w0"]')[i].text
                except:
                    pass
                try:
                    listing_url = driver.find_elements(By.CSS_SELECTOR, '[class="jcs-JobTitle css-jspxzf eu4oa1w0"]')[i].get_attribute('href')
                except:
                    pass
                try:
                    salary = str(driver.find_elements(By.CSS_SELECTOR, '[class="metadata salary-snippet-container"]')[i].text).strip().replace('\n', ' ')
                except:
                    pass
                try:
                    location = str(driver.find_elements(By.CSS_SELECTOR, '[class="companyLocation"]')[i].text).strip().replace('\n', ' ')
                except:
                    pass
                try:
                    job_type = str(driver.find_elements(By.CSS_SELECTOR, '[class="metadata"]')[i].text).strip().replace('\n', ' ').replace(':', '').replace('Job type', '').strip()
                except:
                    job_type = 'Full-Time'
                try:
                    # self.LOGGER.info("Waiting for date posted to become visible]")
                    self.wait_until_visible(driver, css_selector='[class="date"]', duration=3)
                    date_posted = str(driver.find_elements(By.CSS_SELECTOR, '[class="date"]')[i].text).strip().replace('\n', ' ').replace('Posted', '')
                except:
                    date_posted = 'Today'
                try:
                    self.LOGGER.info("Waiting for company name")
                    self.wait_until_visible(driver, css_selector='[class="companyName"]')
                    company_name = job.find_element(By.CSS_SELECTOR, '[class="companyName"]').text
                    # job_url = job.find_element(By.CSS_SELECTOR, '[class="companyName"]').get_attribute('href')
                    job_url = listing_url
                except:
                    pass
                try:
                    # Try switching to iframe, if there is an iframe
                    self.LOGGER.info("Waiting for job side panel iframe")
                    self.wait_until_visible(driver, css_selector='[id="vjs-container-iframe"]', duration=5)
                    self.LOGGER.info("Iframe found")
                    driver.switch_to.frame(driver.find_element(By.CSS_SELECTOR, '[id="vjs-container-iframe"]'))
                    self.LOGGER.info("Switched to iframe")
                except:
                    self.LOGGER.info("Iframe not found")
                    pass
                try:
                    self.wait_until_visible(driver, css_selector='[class="icl-Ratings-count"]', duration=3)
                    reviews = driver.find_element(By.CSS_SELECTOR, '[class="icl-Ratings-count"]').text
                except:
                    reviews = 'Reviews Not Found'
                try:
                    # Switch back to the default content
                    self.LOGGER.info("Switching back from iframe")
                    driver.switch_to.default_content()
                    self.LOGGER.info("Switched back from iframe")
                except:
                    pass
                self.LOGGER.info("Saving job post data")
                job_post = {"Job Title": job_title, "Salary": salary, "Job Type": job_type,
                            "Location": location, "Company Name": company_name, "Date Posted": date_posted,
                            "Reviews": reviews, "Job URL": job_url, "Listing URL": listing_url}
                self.LOGGER.info(f"Job Post: {job_post}")
                df = pd.DataFrame([job_post])
                # if file does not exist write headers
                if not os.path.isfile(file_city):
                    df.to_csv(file_city, index=False)
                else:  # else if exists so append without writing the header
                    df.to_csv(file_city, mode='a', header=False, index=False)
                self.LOGGER.info(f"Data has been saved to:{file_city}")

    def main(self):
        freeze_support()
        self.enable_cmd_colors()
        self.banner()
        self.LOGGER.info(f'IndeedBot launched')
        # thread_counts = self.settings["Settings"]["ThreadCount"]
        cities = pd.read_csv(self.file_cities, index_col=None)
        cities = [city["City"] for city in cities.iloc]
        for city in cities:
            self.get_job_posts(city=city)
        # chunk = round(len(addresses) / thread_counts)
        # address_chunks = [addresses[x:x + chunk] for x in range(len(addresses))]
        # [self.get_address_details(chunk) for chunk in address_chunks]
        # with concurrent.futures.ThreadPoolExecutor(max_workers=thread_counts) as executor:
        #     executor.map(self.get_address_details, address_chunks)
        # self.LOGGER.info(f'Process completed successfully!')


if __name__ == '__main__':
    IndeedBot().main()
