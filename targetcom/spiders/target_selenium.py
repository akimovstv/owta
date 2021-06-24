import time
from shutil import which
from typing import Iterator

from scrapy import Spider
from scrapy.http import TextResponse
from scrapy_selenium import SeleniumRequest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from targetcom.items import TargetcomItem


class TargetSeleniumSpider(Spider):
    """
    This spider extracts required data from html rendered with Selenium web driver.
    """
    name = 'target_selenium'
    allowed_domains = ['target.com']
    custom_settings = {
        'SELENIUM_DRIVER_NAME': 'firefox',
        'SELENIUM_DRIVER_EXECUTABLE_PATH': which('geckodriver'),
        'SELENIUM_DRIVER_ARGUMENTS': ['-headless'],
        'DOWNLOADER_MIDDLEWARES': {'scrapy_selenium.SeleniumMiddleware': 800},
    }

    def start_requests(self) -> Iterator[SeleniumRequest]:
        """
        Generates SeleniumRequest for starting page which is going to wait until price information is in place.
        """
        url = 'https://www.target.com/p/consumer-cellular-apple-iphone-xr-64gb-black/-/A-81406260'
        yield SeleniumRequest(
            url=url,
            callback=self.parse,
            wait_time=10,
            wait_until=EC.visibility_of_element_located((By.XPATH, '//*[@data-test="product-price"]'))
        )

    def parse(self, response: TextResponse, **kwargs) -> Iterator[SeleniumRequest]:
        """
        Parse `response` to extract required data (namely title, price, highlights, description, images) to populate
        an item.
        Generate another SeleniumRequest for Q&A page.
        """
        item = TargetcomItem()

        # Populate item with required data
        item['title'] = response.xpath('//h1[@data-test="product-title"]//text()').get()
        item['price'] = float(response.xpath('//*[@data-test="product-price"]//text()').get().lstrip('$'))
        item['highlights'] = \
            response.xpath('//h3[contains(., "Highlights")]/following-sibling::ul//li//text()').getall()
        item['description'] = \
            '\n'.join(response.xpath('//h3[contains(., "Description")]/following-sibling::div/text()').getall())

        # There are extra images in response (thumbnails, svgs, etc.)
        # We need to take only unique images whose src attribute starts with "http"
        images = \
            response.xpath('//*[@data-test="product-image"]//img[starts-with(@src, "http")]/@src').re(r'(.*?)\?')
        unique_images = list(set(images))
        item['images'] = unique_images

        # Generate request for Q&A page
        yield SeleniumRequest(
            url=response.url + '?showOnlyQuestions=true',
            callback=self.parse_qa,
            cb_kwargs={'item': item},
            wait_time=10,
            wait_until=EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-test="questionSortOrder"]'))
        )

    def parse_qa(self, response: TextResponse, item: TargetcomItem, **kwargs) -> Iterator[TargetcomItem]:
        """
        In response we need to click several times on certain buttons to get question sorted from newest.
        Use WebDriver to click on these buttons.
        """
        driver: WebDriver = response.request.meta['driver']
        # Find "sort by" drop down and click on it
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-test="questionSortOrder"]'))
        ).click()
        # Find "newest questions" option and click on it
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label^="newest questions"]'))
        ).click()

        # After click on "newest questions" we must wait several second while javascript sort questions on the page
        # It is really hard to do calling JavaScript wait, because JavaScript use asynchronous wait (e.g. setTimeout)
        # and it is not going to work with Selenium web driver method `execute_script`
        # So, it was decided to explicitly sleep for 2 seconds, while webdriver render newly run javascript
        time.sleep(2)

        # Populate item with last question and its last answer (if any)
        qa_section = driver.find_element_by_xpath('//*[@data-test="question"]')
        question = qa_section.find_element_by_xpath('//span[@data-test="questionSummary"]').text
        try:
            answer = qa_section.find_element_by_css_selector('ul li:last-child [data-test="answerText"]').text
        except NoSuchElementException:
            answer = None
        item['last_qa'] = {'last_question': question, 'last_answer_for_the_question': answer}
        yield item
