from lxml import html
from fractions import Fraction
# from MySQL.MyDatabase import MyDatabase
from word2number import w2n
from lxml import html
# import pymysql.cursors
import logging
import sys
# import psutil
import time
import traceback
# import yagmail
import settings as scraper_settings
# import pyodbc
import datetime
import decimal
import requests
import json
import re

conn = scraper_settings.DB_CONNECTION

major_keywords = [
    'gold',
    'silver',
    'platinum',
    'palladium'
]


class ExitHooks(object):
    def __init__(self):
        self.exit_code = None
        self.exception = None

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, exc_type, exc, *args):
        self.exception = exc


hooks = ExitHooks()
hooks.hook()


def exit_handler(process_id, scraperLogId, exitFlag=False):
    isActive = 0
    # Log any errors
    if hooks.exit_code is not None:
        logging.info("Exit code sys.exit(%d)" % hooks.exit_code)
        # driver.save_screenshot('scraper screenshots/{website_code}_{filename}.png'.format(website_code=website_code, filename=time.strftime("%Y%m%d-%H%M%S")))
    elif hooks.exception is not None:
        logging.info("Exception: %s" % hooks.exception)
        # driver.save_screenshot('screen.png')
    else:
        logging.info(">> Normal Exit. . .")


def compute_asks(given_price, last_price_option):
    if given_price and last_price_option:
        # Check for invalid price
        if '$--.--' not in [given_price, last_price_option] and 'N/A' not in [given_price, last_price_option]:
            given_price = float(given_price.replace('$', '').replace(',', '').strip())
            last_price_option = float(last_price_option.replace('$', '').replace(',', '').strip())
            return "{0:.2f}".format(given_price - last_price_option)
    return None


def compute_premium(last_price_option, metal_weight, metal_type, gold_spot, silver_spot, platinum_spot, palladium_spot,
                    BBDProductId):
    ceilingPremium = None
    adjustedPremium = None
    metal_weight_oz = None
    cursor = conn.cursor()
    if BBDProductId != 0:
        dbSpotPriceData = cursor.execute(""" EXEC Pricing_GetSpotPrices @ProductID=? """, (BBDProductId))
        dbSpotPrice = dbSpotPriceData.fetchall()
        dbSpot = float(dbSpotPrice[0][0])

    try:
        if (not metal_weight and metal_weight != "No") or metal_weight.strip() == '' or metal_weight.strip() == 'N/A':
            ceilingPremium = "Metal Weight Not Available on Product Detail Page"
            return ceilingPremium, None, None
        spot = None
        metal_weight = metal_weight.lower().replace('round:', '').replace('box:', '').replace('th', '').replace(
            'approx.', '').replace('between', '').replace('o.', '0.').strip()
        if ':' in metal_weight:
            metal_weight = metal_weight[metal_weight.index(':') + 1:].strip()
        if ',' in metal_weight:
            metal_weight = metal_weight[:metal_weight.index(',')].strip()
            metal_weight_unit = 'oz'
        if '-' in metal_weight:
            metal_weight = metal_weight[:metal_weight.index('-')].strip()
            metal_weight_unit = 'oz'
        if 'an ' in metal_weight:
            metal_weight = metal_weight[metal_weight.index('an ') + 3:].strip()
            metal_weight_unit = 'oz'

        if ' ' in metal_weight:
            metal_weight_unit = metal_weight[metal_weight.index(' ') + 1:].strip()
            metal_weight = metal_weight[:metal_weight.index(' ')].strip()
        else:
            if re.findall(r"\d", metal_weight):
                metal_weight_unit = " ".join("".join(re.findall(r"[a-zA-z]+", metal_weight)).split())
                if '/' in metal_weight:
                    metal_weight = " ".join("".join(re.findall(r"\d*\/.?\d+", metal_weight)).split())
                else:
                    metal_weight = " ".join("".join(re.findall(r"\d*\.?\d+", metal_weight)).split())
            else:
                metal_weight_unit = 'oz'

        if '/' in metal_weight:  # If fraction, convert to decimal
            metal_weight_oz = float(sum(Fraction(s) for s in metal_weight.split()))
        else:
            if metal_weight.strip().replace('.', '').isdigit():
                # If already numeric
                metal_weight_oz = float(metal_weight)
            else:
                # Convert word to number
                metal_weight_oz = float(w2n.word_to_num(metal_weight))

        if not metal_weight_oz:  # If weight is 0
            return None, None, 0.0
        if 'oz' not in metal_weight_unit:
            # Conver to oz
            if 'kilo' in metal_weight_unit:
                metal_weight_oz = 32.15 * metal_weight_oz
            elif metal_weight_unit == 'gram' or metal_weight_unit == 'grams' or metal_weight_unit.split(' ')[
                0] == 'gram' or metal_weight_unit.split(' ')[0] == 'grams' or metal_weight_unit == 'g':
                metal_weight_oz = 0.03215 * metal_weight_oz
            elif 'pound' in metal_weight_unit:
                metal_weight_oz = 16 * metal_weight_oz
        elif ('/' in metal_weight_unit and 'oz' in metal_weight_unit) or ('|' in metal_weight_unit):
            if metal_weight_unit == 'gram' or metal_weight_unit == 'grams' or \
                    metal_weight_unit.replace('/', ' ').split(' ')[0] == 'gram' or \
                    metal_weight_unit.replace('/', ' ').split(' ')[0] == 'grams' or \
                    metal_weight_unit.replace('|', ' ').split(' ')[0] == 'grams':
                metal_weight_oz = 0.03215 * metal_weight_oz

        # Validate required values
        if not last_price_option or last_price_option.strip() == '' or last_price_option == 'N/A':
            ceilingPremium = "Price Not Found on Product Detail Page"
            return ceilingPremium, None, metal_weight_oz
        if not metal_type or metal_type.strip() == '':
            ceilingPremium = "Missing metal type value"
            return ceilingPremium, None, metal_weight_oz
        if metal_type == "gold" and (not gold_spot or gold_spot.strip() == ''):
            ceilingPremium = "Gold Spot Price Not Found on Competitor Site"
            return ceilingPremium, None, metal_weight_oz
        if metal_type == "silver" and (not silver_spot or silver_spot.strip() == ''):
            ceilingPremium = "Silver Spot Price Not Found on Competitor Site"
            return ceilingPremium, None, metal_weight_oz
        if metal_type == "platinum" and (not platinum_spot or platinum_spot.strip() == ''):
            ceilingPremium = "Platinum Spot Price Not Found on Competitor Site"
            return ceilingPremium, None, metal_weight_oz
        if metal_type == "palladium" and (not palladium_spot or palladium_spot.strip() == ''):
            ceilingPremium = "Palladium Spot Price Not Found on Competitor Site"
            return ceilingPremium, None, metal_weight_oz

        if metal_type == 'gold':
            gold_spot = float(gold_spot.replace('$', '').replace(',', '').strip())
            spot = gold_spot
        elif metal_type == 'silver':
            silver_spot = float(silver_spot.replace('$', '').replace(',', '').strip())
            spot = silver_spot
        elif metal_type == 'platinum':
            platinum_spot = float(platinum_spot.replace('$', '').replace(',', '').strip())
            spot = platinum_spot
        elif metal_type == 'palladium':
            palladium_spot = float(palladium_spot.replace('$', '').replace(',', '').strip())
            spot = palladium_spot
        print("BBDprodID-",BBDProductId)
        if BBDProductId != 0:
            last_price_option = float(last_price_option.replace('$', '').replace(',', '').strip())
            difference = float("%0.2f" % float(spot - dbSpot))
            if difference < 0:
                difference = abs(difference)
            premiumValue = "{0:.2f}".format((last_price_option / metal_weight_oz) - spot)
            latestPremium = float(premiumValue)
            adjustedPremiumValue = "{0:.2f}".format(latestPremium + difference)
            ceilingPremium = premiumValue
            premium = decimal.Decimal(adjustedPremiumValue)
            print("Premium -",premium)
            lastDigit = premium.as_tuple().digits[-1]
            if lastDigit > 5:
                adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-1] + '5'))
            elif lastDigit == 0:
                lastTwoDigitValue = premium.as_tuple().digits[-2]
                if lastTwoDigitValue == 0:
                    lastTwoDigitValue = '9'
                    lastTwoDigitValue = lastTwoDigitValue + '5'
                    lastThirdDigitValue = premium.as_tuple().digits[-3]
                    if lastThirdDigitValue == 0:
                        lastForthDigitValue = premium.as_tuple().digits[-4]
                        lastThirdDigitValue = '9'
                        if lastForthDigitValue == 0:
                            lastFithDigitValue = premium.as_tuple().digits[-5]
                            lastFithDigitValue = str(lastFithDigitValue - 1)
                            lastForthDigitValue = '9'
                            lastFourDigit = lastForthDigitValue + lastThirdDigitValue + '.' + lastTwoDigitValue
                            lastFithDigit = lastFithDigitValue + lastFourDigit
                            adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-6] + lastFithDigit))
                        else:
                            lastForthDigitValue = str(lastForthDigitValue - 1)
                            lastFourDigit = lastForthDigitValue + lastThirdDigitValue + '.' + lastTwoDigitValue
                            adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-5] + lastFourDigit))
                    else:
                        lastThirdDigitValue = str(lastThirdDigitValue - 1)
                        lastThreeDigit = lastThirdDigitValue + '.' + lastTwoDigitValue
                        adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-4] + lastThreeDigit))
                else:
                    lastTwoDigitValue = str(lastTwoDigitValue - 1)
                    lastTwoDigitValue = lastTwoDigitValue + '5'
                    adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-2] + lastTwoDigitValue))
            else:
                adjustedPremium = "{0:.2f}".format(float(adjustedPremiumValue[0:-1] + '0'))
            return ceilingPremium, adjustedPremium, metal_weight_oz
        else:
            return None, None, metal_weight_oz
    except Exception as e:
        ceilingPremium = "Unable to Compute"
        return ceilingPremium, adjustedPremium, metal_weight_oz


def get_metal_type(driver, product_name, competitorName, xpaths_to_check=[]):
    metal_types = [
        'gold',
        'silver',
        'platinum',
        'palladium'
    ]
    url = driver.current_url.lower()
    source = driver.page_source
    parsed_page = html.fromstring(source)
    m_typeArr = []
    metalType = None
    for m_type in metal_types:
        # Check in url
        if competitorName == 'bullionexchanges' or competitorName == 'libertycoin' or competitorName == 'monarchpreciousmetals':
            if m_type in url:
                m_typeArr.append(m_type)
            else:
                if m_type in product_name.lower().replace('silver gold bull',
                                                          ''):  # Replace string 'silver gold bull' to blank to make comparison more accurate for silver gold bull
                    m_typeArr.append(m_type)
        else:
            # Check in product_name
            if m_type in product_name.lower().replace('silver gold bull',
                                                      ''):  # Replace string 'silver gold bull' to blank to make comparison more accurate for silver gold bull
                m_typeArr.append(m_type)

        # Check by xpath
        for xpath in xpaths_to_check:
            for item in parsed_page.xpath(xpath):
                if m_type in item.lower():
                    return m_type

    if len(m_typeArr) > 1:
        for m_type in m_typeArr:
            if m_type in url:
                metalType = m_type
    elif len(m_typeArr) == 1:
        metalType = ' '.join(''.join(m_typeArr).split())
    else:
        metalType = None

    if competitorName == 'libertycoin' and metalType == None:
        breadCrumbUrl = ' '.join(
            ''.join(parsed_page.xpath('//table//tr/td/a[contains(@title,"Bullion")][3]/text()')).split())
        for m_type in m_typeArr:
            if m_type in breadCrumbUrl.lower():
                metalType = m_type

    return metalType


def save_to_db(CompetitorId, SessionKey, CpId, lst_raw_data):
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM CompetitorJoinedProducts WITH(NOLOCK) where CPId = ?""", (CpId))
        if cursor.rowcount:
            print("LST 19-",lst_raw_data[19])
            if lst_raw_data[19] > 0.0:
                cursor.execute(
                    """SELECT * FROM Competitor_Product_Prices  WITH(NOLOCK) where CPId = ? AND SessionKey=?""",
                    (CpId, SessionKey))
                print(cursor.rowcount)
                if cursor.rowcount:
                    cursor.execute("""
                    UPDATE Competitor_Product_Prices 
                    SET
                        GoldSpotPrice=?, 
                        SilverSpotPrice=?, 
                        PlatinumSpotPrice=?, 
                        PalladiumSpotPrice=?, 
                        Premium=?,
                        PriceTier1=?,
                        Ask1=?,
                        Timestamp=?,
                        PriceNotScrapedAlert=?,
                        AdjustedPremium=?
                    WHERE CPId=? AND SessionKey=? """,
                                   (
                                       lst_raw_data[10],
                                       lst_raw_data[11],
                                       lst_raw_data[12],
                                       lst_raw_data[13],
                                       lst_raw_data[19],
                                       lst_raw_data[15],
                                       lst_raw_data[16],
                                       lst_raw_data[17],
                                       lst_raw_data[18],
                                       lst_raw_data[14],
                                       CpId,
                                       SessionKey
                                   )
                                   )
                    cursor.commit()
                else:
                    prices_insert_sql = """INSERT INTO Competitor_Product_Prices  
                            (CPId,
                            GoldSpotPrice,
                            SilverSpotPrice,
                            PlatinumSpotPrice,
                            PalladiumSpotPrice,
                            Premium,
                            PriceTier1,
                            Ask1,
                            Timestamp,
                            PriceNotScrapedAlert,
                            AdjustedPremium,
                            SessionKey
                            )
                            VALUES
                            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

                    prices_insert_output = [
                        CpId,
                        lst_raw_data[10],
                        lst_raw_data[11],
                        lst_raw_data[12],
                        lst_raw_data[13],
                        lst_raw_data[19],
                        lst_raw_data[15],
                        lst_raw_data[16],
                        lst_raw_data[17],
                        lst_raw_data[18],
                        lst_raw_data[14],
                        SessionKey
                    ]
                    cursor.execute(prices_insert_sql, tuple(prices_insert_output))
                    cursor.commit()
            else:
                errorMessage = str('ProductName:' + lst_raw_data[3] + ' Product Url:' + lst_raw_data[4] +
                                   ' GoldSpotPrice:' + str(lst_raw_data[10]) + ' SilverSpotPrice:' + str(
                    lst_raw_data[11]) +
                                   ' PlatinumSpotPrice:' + str(lst_raw_data[12]) + ' PalladiumSpotPrice:' + str(
                    lst_raw_data[13]) +
                                   ' Premium:' + str(lst_raw_data[14]) + ' PriceTier1:' + str(lst_raw_data[15]))
                updateException(CompetitorId, SessionKey, errorMessage)

        else:
            errorMessage = None
            if lst_raw_data[19] < 0.0:
                errorMessage = str('ProductName:' + lst_raw_data[3] + ' Product Url:' + lst_raw_data[4] +
                                   ' GoldSpotPrice:' + str(lst_raw_data[10]) + ' SilverSpotPrice:' + str(
                    lst_raw_data[11]) +
                                   ' PlatinumSpotPrice:' + str(lst_raw_data[12]) + ' PalladiumSpotPrice:' + str(
                    lst_raw_data[13]) +
                                   ' Premium:' + str(lst_raw_data[14]) + ' PriceTier1:' + str(lst_raw_data[15]))
            else:
                errorMessage = str('ProductName:' + lst_raw_data[3] + ' Product Url:' + lst_raw_data[4] +
                                   ' GoldSpotPrice:' + str(lst_raw_data[10]) + ' SilverSpotPrice:' + str(
                    lst_raw_data[11]) +
                                   ' PlatinumSpotPrice:' + str(lst_raw_data[12]) + ' PalladiumSpotPrice:' + str(
                    lst_raw_data[13]) + ' DataError:' + lst_raw_data[18])
            updateException(CompetitorId, SessionKey, errorMessage)

        # Update Availability
        cursor.execute("""
                    UPDATE CompetitorJoinedproducts 
                    SET ProductName=?,
                        ProductUrl=?,
                        IsPresale=?,
                        IsAvailable=?,
                        IsOutOfStock=?,
                        IsDiscontinued=?,
                        UpdateTS=?
                        WHERE CPId=?
                            """, (
            lst_raw_data[3],
            lst_raw_data[4],
            lst_raw_data[5],
            lst_raw_data[6],
            lst_raw_data[7],
            lst_raw_data[8],
            datetime.datetime.now(),
            CpId))
        cursor.commit()
    except Exception as e:
        errorMessage = str(e)
        print(errorMessage)
        updateException(CompetitorId, SessionKey, errorMessage)
        raise e
    cursor.commit()


def updateException(CompetitorId, SessionKey, errorMessage):
    cursor = conn.cursor()

    cursor.execute(
        """ update ProdCompPriceScraperLog  set 
        EndTime = ?,
        isSuccess = ?,
        ErrorMessage = ?
        where SessionKey =? AND CompetitorId =?
        """,
        (datetime.datetime.now(), 0, errorMessage, SessionKey, CompetitorId)
    )
    cursor.commit()


def AddProdCompPriceScraperLog(competitorId, scraperLogId, SessionKey,CPId):
    prodPriceScraperLog_insert_sql = """INSERT INTO ProdCompPriceScraperLog (ProdScraperLogId,CompetitorId,StartTime, EndTime, isSuccess,CreateTS,SessionKey,CPId)
                VALUES (?, ?, ?, ?, ?, ?, ?,?)"""
    prodPriceScraperLog_insert_output = [scraperLogId, competitorId, datetime.datetime.now(), datetime.datetime.now(),
                                         0, datetime.datetime.now(), SessionKey,CPId]
    cursor = conn.cursor()
    cursor.execute(prodPriceScraperLog_insert_sql, tuple(prodPriceScraperLog_insert_output))
    cursor.commit()


def set_logging(logfile_path):
    # logger = logging.getLogger('metal_logger')
    # if not len(logger.handlers):
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(logfile_path)
    sh = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s] - %(funcName)s - %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')
    fh.setFormatter(formatter)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    # logger.propagate = False
    # return logger


def browser_infinite_scroll(driver, list_xpath):
    SCROLL_PAUSE_TIME = 10
    # Get current list count
    source = driver.page_source
    source_selector = html.fromstring(source)
    last_list_count = len(source_selector.xpath(list_xpath))
    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)
        # Count updated list items
        source = driver.page_source
        source_selector = html.fromstring(source)
        new_list_count = len(source_selector.xpath(list_xpath))
        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height or new_list_count == last_list_count:
            break
        last_list_count = new_list_count
        last_height = new_height


def fatal_exception(process, exceptionkeyword):
    exceptionData = {"process": process, "exceptionDetails": None, "metaData2": None, "metaData3": None}
    headers = {'Content-Type': 'application/json'}
    apiResponse = requests.post(url=scraper_settings.APIURL + "api/Logging/AddFatalExceptions",
                                data=json.dumps(exceptionData), headers=headers)
    logging.info(apiResponse.status_code)


def get_metal_weight(BBDProductId):
    cursor = conn.cursor()
    data = cursor.execute("""SELECT * FROM ProductStats  WITH(NOLOCK) WHERE ProductId=?""", BBDProductId)
    dbData = data.fetchone()
    metal_content = str(dbData[14])
    return metal_content


def getProdPriceScraperLog(competitorId, BBDProductId):
    cursor = conn.cursor()
    data = cursor.execute(
        """SELECT * FROM ProdPriceScraperLog  WITH(NOLOCK) WHERE ProductId=? and CAST(CreateTS as date)=CONVERT(date,?)""",
        (BBDProductId, datetime.datetime.now()))
    dbData = data.fetchone()
    ProdScraperLogId = dbData[0]

    data = cursor.execute(
        """SELECT * FROM ProdCompPriceScraperLog  WITH(NOLOCK) WHERE ProdScraperLogId=? and CAST(StartTime as date)=CONVERT(date,?) and CompetitorId=?""",
        (ProdScraperLogId, datetime.datetime.now(), competitorId))
    dbData = data.fetchone()
    CompPriceScraperLogId = dbData[0]
    return CompPriceScraperLogId