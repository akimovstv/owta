import json
from typing import Iterator
from urllib.parse import urlencode

import chompjs
from scrapy import Request, Spider
from scrapy.http import TextResponse

from targetcom.items import TargetcomItem


class TargetApiSpider(Spider):
    """
    This spider extracts required data from <script> html-elements and additionally making API requests
    to additional services.
    """
    name = 'target_api'
    allowed_domains = ['target.com']
    start_urls = ['https://www.target.com/p/consumer-cellular-apple-iphone-xr-64gb-black/-/A-81406260']

    def parse(self, response: TextResponse, **kwargs) -> Iterator[Request]:
        """
        It seems that some required data is already in the html of `response` inside <script> elements.
        This method translate JavaScript code from such elements to pure Python objects using `chompjs`
        and extract required data (namely title, highlights, description, images) from such objects to populate
        an item.
        It also extracts 2 more urls to get price and q&a information from additional APIs.
        After that it yields a request to get price information to further populate the item.
        """
        # Convert script text with product information to Python object
        script_text = response.xpath('//script[contains(., "__PRELOADED_QUERIES__")]/text()').get()
        preloaded_queries_data = chompjs.parse_js_object(script_text)['__PRELOADED_QUERIES__']['queries']

        # Get meaningful product data
        product_data = preloaded_queries_data[0][1]['data']['product']['item']
        product_description_data = product_data['product_description']
        images_data = product_data['enrichment']['images']

        # Get title, highlights, description, images
        item = TargetcomItem()
        item['title'] = product_description_data['title']
        item['highlights'] = product_description_data['soft_bullets']['bullets']
        item['description'] = product_description_data['downstream_description']
        item['images'] = [images_data['primary_image_url']] + images_data['alternate_image_urls']

        # Extract url to get price from the service. Something like:
        # https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?<parameters>
        price_request_params = preloaded_queries_data[0][0][1]
        price_request_params['key'] = price_request_params.pop('apiKey')
        base_url_for_rest = price_request_params.pop('baseUrlForRest')
        price_url = f'{base_url_for_rest}/pdp_client_v1?{urlencode(price_request_params)}'

        # Extract url for Q&A information. Something like:
        # https://r2d2.target.com/ggc/Q&A/v1/question-answer?<parameters>
        script_text = response.xpath('//script[contains(., "__PRELOADED_STATE__")]/text()').get()
        preloaded_state_data = chompjs.parse_js_object(script_text)['config']
        qa_request_params = {
            'type': 'product',
            'questionedId': price_request_params['tcin'],
            'sortBy': 'MOST_RECENT',
            'key': preloaded_state_data['services']['nova']['apiKey'],
        }
        base_qa_url = preloaded_state_data['services']['nova']['novaQuestionUrl']
        qa_url = f'{base_qa_url}?{urlencode(qa_request_params)}'

        # Ask for price information
        yield Request(url=price_url, callback=self.parse_price, cb_kwargs={'item': item, 'qa_url': qa_url})

    def parse_price(self, response: TextResponse, item: TargetcomItem, qa_url: str, **kwargs) -> Iterator[Request]:
        """
        Extract price information from `response` to populate `item` with and yields a request to get Q&A information
        to further populate the `item`.
        """
        data = json.loads(response.text)
        item['price'] = data['data']['product']['price']['current_retail']
        yield Request(url=qa_url, callback=self.parse_qa, cb_kwargs={'item': item})

    def parse_qa(self, response: TextResponse, item: TargetcomItem, **kwargs) -> Iterator[TargetcomItem]:
        """
        Extract Q&A information from `response` to populate `item` with and yields the `item`.
        """
        data = json.loads(response.text)
        qa = data['results'][0]
        question = qa['text']
        answers = sorted(qa['answers'], key=lambda a: a['submitted_at'], reverse=True)
        answer = answers[0]['text'] if answers else None

        item['last_qa'] = {'last_question': question, 'last_answer_for_the_question': answer}
        yield item
