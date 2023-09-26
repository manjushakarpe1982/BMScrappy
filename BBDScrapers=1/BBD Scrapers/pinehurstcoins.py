from selenium import webdriver

from selenium.webdriver.chrome.options import Options

from lxml import html
# from openpyxl import load_workbook
import datetime
import sys
import os.path as path

# Add path to providentmetals
sys.path.insert(0, path.abspath(path.join(__file__, "../..")))
from time import sleep
import settings as scraper_settings
from random import randint
from decorators import send_error_email_message
import metal_utils
import os
import argparse
import atexit

import logging
import time

from datetime import datetime, timedelta
import re
from selenium.webdriver.chrome.service import Service

# Command argument initialize
parser = argparse.ArgumentParser()
parser.add_argument("-Joined_Products", "--Joined_Products",action='store_true', help="Use this to update JOINED_Products.")
parser.add_argument("-scraperLogId", "--scraperLogId", help="Scraper Log Id used to Insert product Audit .")
parser.add_argument("-ProductId","--ProductId", help=" Id used to get productIdlog." )
parser.add_argument("-Sessionkey","--SessionKey", help=" Id used to get productsessionkey." )
parser.add_argument("-SPCPid","--SPCPid", help=" Id used to get SPCPid." )
parser.add_argument("-update_joined_only", "--update_joined_only", action='store_true', help="Use this to update only JOINED products.")

# Initialize tag if the user only wants to update "JOINED" products
Joined_Products = False
update_joined_only = False

# if update_joined_only flag = True, collect joined products from database
Successcount = []

# Initialize Database connection
conn = scraper_settings.DB_CONNECTION
competitorName = 'Pinehurst Coins'

min_seconds_delay = scraper_settings.MIN_SECONDS_DELAY
max_seconds_delay = scraper_settings.MAX_SECONDS_DELAY
total_product_scraped = 0
competitorId = 0
scraperLogId = 0
groupName = ""
driver = None

dict_main_metals_urls = {}
logfile_path = 'Scraper logs/pinehurstcoins.log'
website_code = 'PH'

# Initalize metal type market summary
goldspotprice = None
silverspotprice = None
platinumspotprice = None
palladiumspotprice = None

def parse_product_page(driver_source, url, CP_Id, CompPriceScraperLogId,BBDProductId):
    from_result_page = False
    cursor = conn.cursor()
    cursor.execute("""select * from CPXpaths WITH(NOLOCK) where CPId=?""",competitorId)
    data = cursor.fetchall()
    col = 3
    productName = data[0][col]
    priceTable = data[6][col]
    priceTier = data[8][col]
    IsAvailable = data[12][col]

    try:
        parsed_page = html.fromstring(driver_source)
        if 'Page Not Found' in driver_source or 'This site can’t be reached' in driver_source:  # Check for product page availability
            # Mark product as "Discontinued"
            cursor.execute("""SELECT * FROM CompetitorJoinedProducts WITH(NOLOCK) where CPId = ?""", (CP_Id,))
            if cursor.rowcount:
                cursor.execute(
                    "UPDATE CompetitorJoinedProducts set IsPresale=?,IsAvailable=?,IsOutOfStock=?,IsDiscontinued=?,UpdateTS=? where CPId=?",
                    (0, 0, 1, 1, datetime.now(), CP_Id))
                cursor.commit()
                logging.info(
                    '>> Product with id "%s" and Url "%s" has been removed from website''\'s listing. This will be considered as "Discontinued incase it exists on the database!' % (
                    CP_Id, url))
                errorMessage = str(
                    'Product with id "%s"  and Url "%s" has been removed from website''\'s listing. This will be considered as "Discontinued incase it exists on the database!' % (
                    CP_Id, url))
                metal_utils.updateException(competitorId, SesionKey, errorMessage)
            else:
                errorMessage = str('Product is Not Available in Database')
                metal_utils.updateException(competitorId, SesionKey, errorMessage)
            return

        pricetier1 = None
        ask1 = None
        last_price_option = None
        premium = None
        adjustedPremium = None
        metal_weight_oz = None

        base_qty_rows = parsed_page.xpath(priceTable+'//tbody/tr[not(contains(., "Qty"))]')
        if len(base_qty_rows) >= 1:
            pricetier1 = ''.join(base_qty_rows[0].xpath(priceTier)).strip() if base_qty_rows[0].xpath(priceTier) else None
            if len(base_qty_rows) > 1:
                priceindex = len(base_qty_rows) -1         
                last_price_option =''.join(base_qty_rows[priceindex].xpath(priceTier)).strip() if base_qty_rows[priceindex].xpath(priceTier) else None
            else:
                last_price_option = pricetier1

        ask1 = metal_utils.compute_asks(pricetier1, last_price_option)

        pricetier1 = 0.0 if  pricetier1 == None else float(pricetier1.replace("$","").replace(",",""))
        #last_price_option = 0.0 if  last_price_option == None else float(last_price_option.replace("$","").replace(",",""))
        ask1 = 0.0 if ask1 == None else float(ask1)



        if not from_result_page:  # Collect all data
            product_name = parsed_page.xpath(productName)[0]
            metal_type = metal_utils.get_metal_type(driver, product_name,competitorName)

            presale = 1 if 'Presale Item' in driver.page_source else 0
            availability = 1 if parsed_page.xpath(IsAvailable) else 0
            outofstock = 1 if not parsed_page.xpath(IsAvailable) else 0
            discontinued = 0

            if presale == 1:
                availability =1

            # other product details
            metal_content = None
            dataError = None

        ### If metal weight not found on product detail page get the metal weight from db
        if metal_content == None and BBDProductId != 0:
            metal_content = metal_utils.get_metal_weight(BBDProductId)
            
            premium,adjustedPremium,metal_weight_oz = metal_utils.compute_premium(
                last_price_option,
                metal_content,
                metal_type,
                goldspotprice,
                silverspotprice,
                platinumspotprice,
                palladiumspotprice,
                BBDProductId
            )
            regex = '[+-]?[0-9]+\.[0-9]+'
            if premium:
                if (re.search(regex, premium)):
                    premium = float(premium)
                    adjustedPremium = float(adjustedPremium)
                    metal_weight_oz = float(metal_weight_oz)
                else:
                    dataError = premium
                    premium = 0.0
                    adjustedPremium = 0.0

            if dataError == 'Price Not Found on Product Detail Page':
                availability = 0
                outofstock = 1
                logging.info('>>Updating out of stock due to price not available on detail page:%s' % CP_Id)
                metal_utils.updateException(competitorId,SesionKey,'Updating out of stock due to price not available on detail page')

            else :
                dataError= 'Scraped ! !'
                
        lst_raw_data = [
            competitorId,
            CP_Id,
            competitorName,
            product_name,
            url,
            presale,
            availability,
            outofstock,
            discontinued,
            metal_content,
            float(goldspotprice.replace("$","").replace(",","")),
            float(silverspotprice.replace("$","").replace(",","")),
            float(platinumspotprice.replace("$","").replace(",","")),
            float(palladiumspotprice.replace("$","").replace(",","")),
            adjustedPremium,
            pricetier1,
            ask1,
            datetime.now(), 
            dataError,
            premium,
            metal_weight_oz
        ]

        logging.info('Data:%s'%lst_raw_data)
        if availability == 1:
            cursor = conn.cursor()
            cursor.execute(""" select * From ProdPriceScraperLog  WITH(NOLOCK) Where SessionKey = ?  """, SesionKey)
            Productpricescraperlog = cursor.fetchone()
            data = Productpricescraperlog.SuccessfulScrapedCompetitorCnt
            print('DATA----', data)
            Successcountscraped = Productpricescraperlog.SuccessfulScrapedCompetitorCnt + 1
            print('Successcount=-----', Successcountscraped)
            cursor.execute(
                "UPDATE ProdPriceScraperLog set SuccessfulScrapedCompetitorCnt=?, EndTime= ? where SessionKey=?",
                (Successcountscraped, datetime.now(), SesionKey))
            cursor.commit()
            metal_utils.save_to_db(competitorId, SesionKey, CP_Id, lst_raw_data)
        else:
            if outofstock == 1:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE CompetitorJoinedProducts set IsAvailable=0,IsDiscontinued=0,IsPresale=0,IsOutOfStock=?,UpdateTS=? where CPId=?",
                    (outofstock, datetime.now(), CP_Id))
                cursor.commit()
                logging.info('>> Skipping "Out Of Stock" product with product ID : %s' % CP_Id)
                metal_utils.updateException(competitorId, SesionKey, 'Skipping "Out Of Stock" product with product')


    except Exception as e:
        errorMessage = str(e)
        print('SAVE DB ERR------', errorMessage)
        metal_utils.updateException(competitorId, SesionKey, errorMessage)

def parse_search_result(driver_source):
    prodLogId = 0
    CompPriceScraperLogId= 0
    cursor.execute("""select * from CPXpaths WITH(NOLOCK) where CPId =?""", competitorId)
    data = cursor.fetchall()
    col = 3
    productUrl = data[2][col]

    try:
        SP_CPid = SPCPid
        print('SP_CPid--', SP_CPid)
        cursor.execute("""SELECT * FROM CompetitorJoinedProducts WITH(NOLOCK) where  CPId=? """, SP_CPid)
        data1 = cursor.fetchone()
        if data1.IsIgnored == 0:
            CP_Id = data1.CPId
            product_href = data1.ProductUrl
            logging.info('>> Updating "JOINED" and not "Ignored" product with product ID : %s' % CP_Id)
            BBDProductId = Productid
            navigate_to_product_page(product_href, CP_Id, CompPriceScraperLogId, BBDProductId)
        else:
            logging.info('>> Skipping "Ignored" product with product ID : %s' % SP_CPid)
            metal_utils.updateException(competitorId, SesionKey, 'Skipping "Ignored" product')

    except Exception as e:
        errorMessage = str(e)
        metal_utils.updateException(competitorId, SesionKey, errorMessage)


def navigate_to_product_page(product_href, CP_Id, CompPriceScraperLogId, BBDProductId):
    logging.info('>> Navigating to product page URL : %s' % product_href)
    # SAve original tabl
    curWindowHndl = driver.current_window_handle
    # open tab
    driver.execute_script("window.open('about:blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(product_href)
    sleep(3)
    # delay before navigating on next product page
    sleep(randint(min_seconds_delay, max_seconds_delay))
    parse_product_page(driver.page_source, driver.current_url, CP_Id, CompPriceScraperLogId,BBDProductId)
    # close tab
    driver.close()
    # Restore window handle
    driver.switch_to.window(curWindowHndl)


def close_modal():
    modal_appeared = False
    # Close modal
    try:
        shh_modal_close = driver.find_element_by_xpath('//div[@id="sgcboxLoadedContent"]//a[@class="sg-popup-close"]')
        shh_modal_close.click()
        modal_appeared = True
    except:
        pass

    return modal_appeared

def select_max_results_option():
    sixty_results_link = driver.find_element_by_xpath('//select[@id="p-pagesize-bottom"]/option[contains(text(), "120")]')
    sixty_results_link.click()


if __name__ == '__main__':
    try:
        # Set logging
        metal_utils.set_logging(logfile_path)
        # Parse arguements
        args = parser.parse_args()
        scraperLogId = args.scraperLogId
        Productid= args.ProductId
        SesionKey= args.SessionKey
        SPCPid = args.SPCPid

        str_date_today = time.strftime('%Y-%m-%d')
        #schedule_time = args.schedule_time
        update_joined_only = args.update_joined_only
        process_id = os.getpid()
        # Regegister Exit handler
        atexit.register(metal_utils.exit_handler, process_id,scraperLogId)

        logging.info('>> Process ID: %s' % process_id)

        if update_joined_only:
            logging.info('>> This instance will only update prices for "JOINED" products.')
            # Collect joined products for this dealer that are not yet updated today
            # schedule_date = datetime.datetime.strptime(schedule_time, '%Y-%m-%d %H:%M:%S').date()
            cursor = conn.cursor()
            cursor.execute("""SELECT * FROM Competitors WITH(NOLOCK) where Name=?""",competitorName)
            competitors = cursor.fetchone()
            competitorId = competitors.Id
            groupName = competitors.Grouping	
            detailUrl = competitors.DetailUrl
            isActive = int(competitors.IsActive)
            # Insert Data into Competitor Log table
            CompPriceScraperLogId = metal_utils.AddProdCompPriceScraperLog(competitorId, scraperLogId, SesionKey,
                                                                           SPCPid)

            cursor.execute("""SELECT * FROM CPXpaths WITH(NOLOCK) where CPId=?""",competitorId)
            data = cursor.fetchall()
            col = 3
            goldSpotPrice = data[2][col]
            silverSpotPrice = data[3][col]
            platinumSpotPrice = data[4][col]
            palladiumSpotPrice = data[5][col]

            # Open Chrome Driver
            logging.info('>> Opening Invisible Browser. . .')
            # Add options to make chrome headless
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('log-level=3')

            try:
                # Chrome driver
                driver_path = scraper_settings.DRIVER_PATH
                driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
                # Set browser size
                driver.set_window_size(1366, 768)
                # driver_path = scraper_settings.DRIVER_PATH
                # s = Service(driver_path)
                # driver = webdriver.Chrome(service =s,options=chrome_options)

                # Close excess tab from initial loading
                if '--headless' not in chrome_options.arguments and len(driver.window_handles) > 1:
                    curWindowHndl = driver.window_handles[0]
                    driver.switch_to.window(driver.window_handles[1])
                    driver.close()
                    # Restore window handle
                    driver.switch_to.window(curWindowHndl)

            except Exception as e:
                logging.info("Error:%s"%e)
                driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
                # driver = webdriver.Chrome(service =s,options=chrome_options)
                
            logging.info('>> Navigating to '+detailUrl+'.')
            driver.get(detailUrl)
            
            # Immediately parse spot prices
            main_page = html.fromstring(driver.page_source)
            goldspotprice = main_page.xpath('//div[@class="spot-pricing-marquee static"]//li[@class="metal-gold"]/div[2]/text()')[0]
            silverspotprice = main_page.xpath('//div[@class="spot-pricing-marquee static"]//li[@class="metal-silver"]/div[2]/text()')[0]
            platinumspotprice = main_page.xpath('//div[@class="spot-pricing-marquee static"]//li[@class="metal-platinum"]/div[2]/text()')[0]
            palladiumspotprice = main_page.xpath('//div[@class="spot-pricing-marquee static"]//li[@class="metal-palladium"]/div[2]/text()')[0]

            goldspotprice = str(goldspotprice)
            silverspotprice= str(silverspotprice)
            platinumspotprice= str(platinumspotprice)
            palladiumspotprice= str(palladiumspotprice)

            pageSource = None
            parse_search_result(pageSource )
            '''
            search_again = raw_input(">> Search again?(y/n): ")
            if search_again.strip() in ['y', 'Y']:
                global total_product_scraped
                total_product_scraped = 0
                pass
            else:
                break
                '''
            # conn.close()

        else:
            atexit.register(metal_utils.exit_handler, process_id, scraperLogId, exitFlag=True)
    except Exception as e:
        logging.info('Error:%s' % e)
        errorMessage = str(e)
        print(errorMessage)
        metal_utils.updateException(competitorId, SesionKey, errorMessage)
        process = os.path.basename(sys.modules['__main__'].__file__)
        metal_utils.fatal_exception(process, errorMessage)
        raise
    finally:
        if driver != None:
            driver.quit()
        else:
            pass