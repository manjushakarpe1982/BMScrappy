
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
from datetime import datetime
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
competitorName = 'Monument Metals'

min_seconds_delay = scraper_settings.MIN_SECONDS_DELAY
max_seconds_delay = scraper_settings.MAX_SECONDS_DELAY
total_product_scraped = 0
competitorId = 0
scraperLogId = 0
groupName = ""
driver = None

dict_main_metals_urls = {}
logfile_path = 'Scraper logs/monumentmetals.log'
website_code = 'MU'

def parse_product_page(driver_source, url, CP_Id, CompPriceScraperLogId,BBDProductId):
    logging.info('<<get the driver source>>>>>>>: %s'% driver_source)
    from_result_page = False
    cursor = conn.cursor()
    cursor.execute("""select * from CPXpaths WITH (NOLOCK) where CPId=?""",competitorId)
    data = cursor.fetchall()
    col = 3
    productName = '//*[@class="productFullDetail-title-4X6 mb-2.5 lg_mb-5"]//h1/text()'
    IsAvailable = '//*[@class="productFullDetail-inStock-39d text-green font-semibold"]/text()'
    IsPresale = '//*[@class="productFullDetail-preorder-2KP text-gold font-semibold"]/text()'
    IsOutofStock = '//*[@class="productFullDetail-outOfStock-1xe text-red-light font-semibold"]/text()'
    goldSpotPrice = '//div[@class="priceBar-priceEntry-HMg flex items-end lg_justify-center lg_px-0 lg_w-[292px] lg_my-3.75 lg_relative"]//span[2]/text()'
    silverSpotPrice = '//div[@class="priceBar-priceEntry-HMg flex items-end lg_justify-center lg_px-0 lg_w-[292px] lg_my-3.75 lg_relative"]//span[2]/text()'
    platinumSpotPrice = '//div[@class="priceBar-priceEntry-HMg flex items-end lg_justify-center lg_px-0 lg_w-[292px] lg_my-3.75 lg_relative"]//span[2]/text()'
    palladiumSpotPrice = '//div[@class="priceBar-priceEntry-HMg flex items-end lg_justify-center lg_px-0 lg_w-[292px] lg_my-3.75 lg_relative"]//span[2]/text()'
    priceTable = '//*[@class="priceBlock-table-16C w-full text-sm"]'
    priceTier = './/td[2]/span/text()'
    productDetailsTable = '//ul[contains(@class, "productFullDetail-additionalInfoList-3Bp lg_flex lg_flex-wrap lg_mt-9 lg_gap-y-1.5 lg_gap-x-7.5")]/li'
    productDetailsLabel = '//ul[contains(@class, "productFullDetail-additionalInfoList-3Bp lg_flex lg_flex-wrap lg_mt-9 lg_gap-y-1.5 lg_gap-x-7.5")]/li/text()'
    productDetailsValue = '//ul[contains(@class, "productFullDetail-additionalInfoList-3Bp lg_flex lg_flex-wrap lg_mt-9 lg_gap-y-1.5 lg_gap-x-7.5")]/li//span/text()'

    # logging.info('<<calling all the xpaths: %s'% driver_source)

    try:
        # logging.info('<<calling all the xpaths:in try block')
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

        qtytier1 = None
        pricetier1 = None
        ask1 = None
        last_price_option = None
        premium = None
        adjustedPremium = None
        metal_weight_oz = None

        # Metal price
        #try:
        # logging.info('<<calling xpath of gold price:')
        # logging.info('<<calling parsed_page :%s '%html.tostring(parsed_page, pretty_print=True, encoding='utf-8').decode('utf-8'))
        
        # goldspotprice = ' '.join(parsed_page.xpath(goldSpotPrice))
        # logging.info('goldspotprice:%s'%goldspotprice)
        # logging.info('goldspotprice: with split%s'%goldspotprice.split[0])
        # silverspotprice = ' '.join(parsed_page.xpath(silverSpotPrice))
        # platinumspotprice = ' '.join(parsed_page.xpath(platinumSpotPrice))
        # palladiumspotprice = ' '.join(parsed_page.xpath(palladiumSpotPrice))
        

        goldspotprice = parsed_page.xpath(goldSpotPrice)[0].strip()
        silverspotprice = parsed_page.xpath(silverSpotPrice)[1].strip()
        platinumspotprice = parsed_page.xpath(platinumSpotPrice)[2].strip()
        palladiumspotprice = parsed_page.xpath(palladiumSpotPrice)[3].strip()
        
        print('goldspotprice:',goldspotprice)
        print('silverspotprice:-',silverspotprice)
        print('platinumspotprice:-',platinumspotprice)
        print('palladiumspotprice',palladiumspotprice)

        # logging.info('<<print xpath of gold price:')

        # except Exception:
        #     cursor.execute("""select * from SpotPrices order by id desc""")
        #     data = cursor.fetchall()
        #     goldspotprice = '$' + str(data[0][2])
        #     silverspotprice = '$' + str(data[0][3])
        #     platinumspotprice = '$' + str(data[0][4])
        #     palladiumspotprice = '$' + str(data[0][5])

        base_qty_rows = parsed_page.xpath(priceTable + '//tbody/tr')
        base_price_row = parsed_page.xpath(priceTable+'//tbody/tr/td[contains(@class,"priceBlock-price-2Tf")]')
        row_count = round(len(base_price_row)/2)

        if row_count >= 1:
            pricetier1 = ''.join(base_qty_rows[0].xpath(priceTier)).strip() if base_qty_rows[0].xpath(priceTier) else None
            if row_count > 1:
                priceindex = row_count -1         
                last_price_option = ''.join(base_qty_rows[priceindex].xpath(priceTier)).strip() if base_qty_rows[priceindex].xpath(priceTier) else None
            else:
                last_price_option = pricetier1

        ask1 = metal_utils.compute_asks(pricetier1, last_price_option)

        pricetier1 = 0.0 if  pricetier1 == None else float(pricetier1.replace("$","").replace(",",""))
        #last_price_option = 0.0 if  last_price_option == None else float(last_price_option.replace("$","").replace(",",""))
        ask1 = 0.0 if ask1 == None else float(ask1)

        if not from_result_page:  # Collect all data
            product_name = parsed_page.xpath(productName)[0]
            metal_type = metal_utils.get_metal_type(driver, product_name, competitorName)


            presale = presale = 1 if parsed_page.xpath(IsPresale) else 0
            availability = 1 if parsed_page.xpath(IsAvailable) else 0
            outofstock = 1 if parsed_page.xpath(IsOutofStock) else 0
            discontinued = 0

            if presale == 1:
                availability =1

                        # other product details
            metal_content = None
            # ira_eligible = 'Yes' if 'Eligible for' in driver.page_source and 'Precious Metals IRAs' in driver.page_source else 'No'
            dataError = None

            # product_details_table_rows = parsed_page.xpath(productDetailsTable)
            # for detail in product_details_table_rows:
            #     label = detail.xpath(productDetailsLabel)[0].strip()
            #     value = detail.xpath(productDetailsValue)[0].strip()
            #     if label == 'Metal Content:':
            #         metal_content = value
            
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
        # logging.info('float(goldspotprice)%f'%float(goldspotprice.replace("$","").replace(",","")))
        # logging.info('Data:%s'%lst_raw_data)
        
        if availability == 1:

            cursor = conn.cursor()
            # logging.info('cursor')
            cursor.execute(""" select * From ProdPriceScraperLog  WITH(NOLOCK) Where SessionKey = ?  """, SesionKey)
            # logging.info('execute')
            Productpricescraperlog = cursor.fetchone()
            data = Productpricescraperlog.SuccessfulScrapedCompetitorCnt
            print('DATA----', data)
            Successcountscraped = Productpricescraperlog.SuccessfulScrapedCompetitorCnt + 1
            print('Successcount=-----', Successcountscraped)
            cursor.execute(
                "UPDATE ProdPriceScraperLog set SuccessfulScrapedCompetitorCnt=?, EndTime= ? where SessionKey=?",
                (Successcountscraped, datetime.now(), SesionKey))
            cursor.commit()
            # logging.info('commit')
            metal_utils.save_to_db(competitorId, SesionKey, CP_Id, lst_raw_data)

            # logging.info('data_1:-%s'%data)
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
        logging.info('>>SAVE DB ERR------', errorMessage)
        metal_utils.updateException(competitorId, SesionKey, errorMessage)

def parse_search_result(driver_source):
    prodLogId = 0
    CompPriceScraperLogId= 0
    cursor.execute("""select * from CPXpaths WITH (NOLOCK) where CPId =?""", competitorId)
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
        # logging.info('>>parse_search_result------%s'%errorMessage)
        metal_utils.updateException(competitorId, SesionKey, errorMessage)


def navigate_to_product_page(product_href, product_id, CompPriceScraperLogId, BBDProductId):
    logging.info('>> Navigating to product page URL : %s' % product_href)
    # SAve original tabl
    curWindowHndl = driver.current_window_handle
    # open tab
    driver.execute_script("window.open('about:blank');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(product_href)
    # logging.info('>>get the product href.......')#####
    sleep(5)
    # delay before navigating on next product page
    sleep(randint(min_seconds_delay, max_seconds_delay))
    # logging.info('<<<< go to the parsr_product_page>>>>>>>>>')
    # # logging.info('<<<page_source : %s' % driver.page_source )
    # logging.info('<<<current_url: %s' % driver.current_url )
    # logging.info('<<<product_id %s' % product_id )
    # logging.info('<<<CompPriceScraperLogId %s' % CompPriceScraperLogId )
    # logging.info('<<<BBDProductId %s' % BBDProductId )
    parse_product_page(driver.page_source, driver.current_url, product_id, CompPriceScraperLogId,BBDProductId)
    # logging.info('<<<< go to the parsr_product_page' % driver.current_url )

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
            cursor.execute("""SELECT * FROM Competitors WITH (NOLOCK) where Name=?""",competitorName)
            competitors = cursor.fetchone()
            competitorId = competitors.Id
            groupName = competitors.Grouping	
            detailUrl = competitors.DetailUrl
            isActive = int(competitors.IsActive)

            # Insert Data into Competitor Log table
            CompPriceScraperLogId = metal_utils.AddProdCompPriceScraperLog(competitorId, scraperLogId, SesionKey,
                                                                           SPCPid)

            # Open Chrome Driver
            logging.info('>> Opening Invisible Browser. . .')
            # Add options to make chrome headless
            chrome_options = Options()
            #chrome_options.add_argument("--headless")
            chrome_options.add_argument('log-level=3')

            try:
                # Chrome driver
                driver_path = scraper_settings.DRIVER_PATH
                driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
                # Set browser size
                driver.set_window_size(1300, 700)
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
                logging.info("Error:%s" % e)
                # logging.info('>>update_joined_only------', e)
                driver = webdriver.Chrome(executable_path=driver_path, chrome_options=chrome_options)
                # driver = webdriver.Chrome(service =s,options=chrome_options)

            logging.info('>> Navigating to ' + detailUrl + '.')
            driver.get(detailUrl)
            # while True:
            # Input
            # keyphrase = ' '.join(sys.argv[1:]).strip() #raw_input(">> Enter keyword to be searched: ").strip()
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
        # logging.info('>>Main------', errorMessage)
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