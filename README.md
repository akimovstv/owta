# OpsWorks test assignment

## Task
```text
Please scrape the following link:
https://www.target.com/p/consumer-cellular-apple-iphone-xr-64gb-black/-/A-81406260#lnk=sametab and extract the following data.

- product title
- product price
- product images(in simple path format no need to download data)
- product description
- product highlights
- last question and last answer asked

Provide the implementation in Scrapy. Load the data into Item, simple output in the terminal. Push the final version of the scraper into a git repo, please. 

Show your best Python skills!
Good luck :)
```

## Implementation

Two Scrapy spiders that parse provided page (and similar pages (tested (not thoroughly))).

### 1. Spider target_api
[target_api.py](targetcom/spiders/target_api.py) is a spider that uses API calls which I found out analyzing 
outgoing requests with Chrome and Firefox developer tools.  
I think that finding data source is the most preferable way of parsing any data, and
[Scrapy documentation](https://docs.scrapy.org/en/latest/topics/dynamic-content.html#finding-the-data-source)
suggest exactly the same.  
This spider is very fast.

### 2. Spider target_selenium
[target_selenium.py](targetcom/spiders/target_selenium.py) is a spider that uses headless firefox through selenium 
web driver. It was created just to test myself in Xpath and CSS selectors and JavaScript rendering. 
Spiders that render JavaScript are slow. This one is slow as well.

**It assumes that `geckodriver` is reachable from current working directory.**  
You can download `geckodriver` from here https://github.com/mozilla/geckodriver/releases.
You can read more about Driver requirements in official 
[Selenium documentation](https://www.selenium.dev/documentation/en/webdriver/driver_requirements/).

## Running
To run the spiders call (do not forget to install requirements from [requirements.txt](requirements.txt)):
```shell
scrapy crawl --nolog target_api
```
```shell
scrapy crawl --nolog target_selenium
```
These commands will print scraped items to `std.out`.

I pre-run the commands and save scraped items in [assets](assets) just for reference.

---

**P.S.** It took me way more than 2 hours to implement these 2 spiders.  
**P.P.S.** I used Python 3.9.5.