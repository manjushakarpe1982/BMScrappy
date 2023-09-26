import os, sys
import os.path as path
import logging
import datetime
import time

import settings as scraper_settings

sys.path.insert(0, path.abspath(path.join(__file__ ,"../..")))
max_running_crawler_per_dealer = scraper_settings.MAX_RUNNING_CRAWLER_PER_DEALER

conn = scraper_settings.DB_CONNECTION
count = 0
cursor = conn.cursor()
schedulerData = []





if __name__ == '__main__':
    try:
        # Set logging
        logger = logging.getLogger('')
        logger.setLevel(logging.INFO)
        fh = logging.FileHandler('history.log')
        sh = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('[%(asctime)s] - %(funcName)s - %(message)s', datefmt='%a, %d %b %Y %H:%M:%S')
        fh.setFormatter(formatter)
        sh.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(sh)

        process_id = os.getpid()


        logging.info('>> Schedule service has been started. . .')
        
        cursor = conn.cursor()
        cursor.execute(""" set nocount on; EXEC Scraper_GetProducttoScrape @ScraperServerCode = 'BS-3',@isTrending=0 """)#LOOP FOR PROD ID
        Products_to_Scraped = cursor.fetchall()
        product_id = 0
        Cpid =0
        SessionKey = None
        LastScrapedDate = datetime.datetime.now()
        logging.info('BS-1:%s'%Products_to_Scraped)
        print('lastscrapeddate: ', LastScrapedDate)
        cmd_count = 0
        for idx, Product_to_Scraped in enumerate(Products_to_Scraped):
            logging.info('Loop%s'%Product_to_Scraped)
            cursor.execute(""" select Top 1 * From ProdPriceScraperLog WITH(NOLOCK) Where isComplete = 0 and ProductId = ? and CAST(CreateTS as date)= CAST (getdate()as date) order by CreateTS desc """, Product_to_Scraped.ProductId )
            Productpricescraperlog = cursor.fetchone()
            TotalJoinedCompetitor = Product_to_Scraped.TotalJoinedCompetitors

            if Productpricescraperlog != None :
                # print('product price scraper log is null')
                IsComplete = 0
                LastScrapedDate = Productpricescraperlog.CreateTS
                ScrapedCompetitorCount = Productpricescraperlog.ScrapedCompetitorCount + 1

                

                if ScrapedCompetitorCount == TotalJoinedCompetitor :
                    IsComplete = 1

                cursor.execute("""Update ProdPriceScraperLog SET  ScrapedCompetitorCount = ?, isComplete = ? where SessionKey =? """, (ScrapedCompetitorCount, IsComplete,  Productpricescraperlog.SessionKey))
                cursor.commit()
                print('updated=====================')

            else :
                LastScrapedDate = datetime.datetime.now() - datetime.timedelta(days= 1)
                print('lastscrapeddate=====',LastScrapedDate)

            # Check the time between current time and lastRunTime.
            if Product_to_Scraped.ProductId != product_id :
                differancetime= datetime.datetime.now() - LastScrapedDate
                Time = differancetime.total_seconds() / 60

                #Create session key
                product_id = Product_to_Scraped.ProductId
                if product_id != 0 and Time > 240:

                    now = datetime.datetime.now()
                    date_string = now.strftime("%Y-%m-%d")
                    time_string = now.strftime("%H-%M-%S")
                    SessionKey = date_string + '_' + time_string +'_'+ str (product_id)

                    scraperLog_insert_sql = """INSERT INTO ProdPriceScraperLog(ProductId, StartTime, isSuccess, ScrapedCompetitorCount,
                                        SuccessfulScrapedCompetitorCnt, FailureScrapedCompetitorCnt, CreateTS,
                                        SessionKey, isComplete)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                    scraperLog_insert_output = [product_id,datetime.datetime.now(), 0, 1,0, 0, datetime.datetime.now(), SessionKey, 0]

                    cursor.execute(scraperLog_insert_sql, tuple(scraperLog_insert_output))
                    cursor.commit()

                else:
                    SessionKey = Productpricescraperlog.SessionKey

            data = cursor.execute("select * From ProdPriceScraperLog WITH(NOLOCK) where SessionKey= ?",SessionKey)
            LogId = data.fetchone()
            scraperLogId = LogId.Id

            CompetitorId=Product_to_Scraped.CompetitorId
            product_id = Product_to_Scraped.ProductId
            Script_name = Product_to_Scraped.ScriptName
            SPCPid= Product_to_Scraped.CPId


            #generate cmd argument.
            command = 'python {} --Joined_Products --scraperLogId={} --ProductId={} --SessionKey={} --SPCPid={} --update_joined_only '.format( Script_name, scraperLogId, product_id, SessionKey, SPCPid )
            print(command)
            os.system("start /min cmd /c {command}".format(command=command))
            time.sleep(20)
        sys.exit()

    except Exception as e:
        errorMessage = str(e)
        print(errorMessage)
        raise



