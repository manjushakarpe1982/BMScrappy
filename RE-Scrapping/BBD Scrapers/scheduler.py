import os, sys
import os.path as path
import logging
import datetime
import subprocess
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
        
        scrapers_folder = scraper_settings.COMPETITOR_SOURCE_FILE_PATH

        logging.info('>> Schedule service has been started. . .')
        
        cursor = conn.cursor()
        cursor.execute(""" set nocount on; EXEC Scraper_GetRescrapeProduct """)#LOOP FOR PROD ID

        Products_to_Scraped = cursor.fetchall()
        # print('Products_to_Scraped',Products_to_Scraped)
        for idx,product in enumerate(Products_to_Scraped):
            Script_name = product.ScriptName
            scraperLogId = product.ProdScraperLogId
            product_id = product.ProductId
            SessionKey = product.SessionKey
            SPCPid = product.CPId

            cursor.execute(""" select Top 1 * From ProdPriceScraperLog WITH(NOLOCK) Where ProductId = ? and SessionKey = ?  """, (product_id,SessionKey) )
            Productpricescraperlog = cursor.fetchone()
            TotalJoinedCompetitor = product.TotalJoinedCompetitors

            if Productpricescraperlog != None :
                # print('product price scraper log is null')
                IsComplete = 0
                ScrapedCompetitorCount = Productpricescraperlog.ScrapedCompetitorCount + 1

                if ScrapedCompetitorCount == TotalJoinedCompetitor :
                    IsComplete = 1

                cursor.execute("""Update ProdPriceScraperLog SET  ScrapedCompetitorCount = ?, isComplete = ? where SessionKey =? """, (ScrapedCompetitorCount, IsComplete,  SessionKey))
                cursor.commit()
                print('updated=====================')

            #generate cmd argument.
            command = 'python {} --Joined_Products --scraperLogId={} --ProductId={} --SessionKey={} --SPCPid={} --update_joined_only '.format( Script_name, scraperLogId, product_id, SessionKey, SPCPid )
            print(command)
            # subprocess.Popen(command)
            os.system("start /min cmd /c {command}".format(command=command))
            time.sleep(20)
        sys.exit()

    except Exception as e:
        errorMessage = str(e)
        print(errorMessage)
        raise



