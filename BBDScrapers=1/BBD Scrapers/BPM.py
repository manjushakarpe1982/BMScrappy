# from openpyxl import load_workbook
import datetime
import sys
import os.path as path

# Add path to providentmetals
sys.path.insert(0, path.abspath(path.join(__file__, "../..")))
from time import sleep
import settings as scraper_settings
from random import randint
import metal_utils
import argparse
import pyodbc
from datetime import datetime, timedelta


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

#deifne_comp_nmae
competitorName = 'BoldPreciousMetals'

#define-db-connection
conn = scraper_settings.DB_CONNECTION
cursor = conn.cursor()

args = parser.parse_args()
scraperLogId = args.scraperLogId
Productid= args.ProductId
SesionKey= args.SessionKey
SPCPid = args.SPCPid

update_joined_only = args.update_joined_only

cursor = conn.cursor()
cursor.execute("""SELECT * FROM Competitors  WITH(NOLOCK) where Name=?""",competitorName)
competitors = cursor.fetchone()
competitorId = competitors.Id


try:
    SPProductId= Productid
    print('SP_CPid--',SPProductId)
    cursor.execute("""SELECT * FROM CompetitorJoinedProducts WITH(NOLOCK) where CompetitorId= 30 and  BBDProductId=? """,SPProductId)
    data1=cursor.fetchone()
    if data1.IsIgnored == 0:
        ProductSKU = data1.BBDSKU
        CPId=data1.CPId
        CompPriceScraperLogId = metal_utils.AddProdCompPriceScraperLog(competitorId,scraperLogId, SesionKey,SPCPid)
    else:
        metal_utils.updateException(competitorId,SesionKey,'Skipped ignored product')
except Exception as e:
    errorMessage = str(e)
    print('ERR',errorMessage)
    metal_utils.updateException(competitorId,SesionKey,errorMessage)


if ProductSKU != 0:
    #prod-DB-connection
    conn_source = pyodbc.connect('DRIVER={SQL Server};SERVER=208.51.60.144;DATABASE=BPMProd;UID=BPMProdUser;PWD=Bold$2020#SQLUser')
    cursor_source = conn_source.cursor()
    
    #invoke_SP
    data = cursor_source.execute(""" set nocount on; EXEC GetProductInfoBBD @ProductSKU=?""", (ProductSKU))
    row = data.fetchall()
    print('DATA----',row)
     
    try:
        # Joined-Product table Updation
        cursor.execute("UPDATE CompetitorJoinedProducts set IsPresale=?,IsAvailable=?,IsOutOfStock=?,UpdateTS=?  where CPId=?",((list(row[0]))[1], (list(row[0]))[2], (list(row[0]))[3], datetime.now(), SPCPid))
        cursor.commit
        print('DB Updated CJP....!!!!')

        #Product Price Updation
        print('CPID---',CPId)
        
        cursor.execute("select * From Competitor_Product_Prices WITH(NOLOCK) where CPId = ? AND SessionKey=?", CPId,SesionKey )
        cursor.fetchone()

        #Competitor_Product_Prices table Updation
        if cursor.rowcount:
            cursor.execute("UPDATE Competitor_Product_Prices set GoldSpotPrice=?, SilverSpotPrice=?, PlatinumSpotPrice=?, PalladiumSpotPrice=?, Premium=?, PriceTier1=?, Ask1=?, Timestamp= ? where CPId=? AND SessionKey=?",((list(row[0]))[8], (list(row[0]))[9], (list(row[0]))[10], (list(row[0]))[11], (list(row[0]))[4], (list(row[0]))[7], (list(row[0]))[5], datetime.now(),CPId,SesionKey))
            cursor.commit()
        else :
            prices_insert_sql = """
                INSERT INTO 
                    Competitor_Product_Prices
                    (CPId,
                    GoldSpotPrice,
                    SilverSpotPrice,
                    PlatinumSpotPrice,
                    PalladiumSpotPrice,
                    Premium,
                    PriceTier1,
                    Ask1,
                    Timestamp,
                    SessionKey
                    )
                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

            prices_insert_output = [
                    CPId,
                    (list(row[0]))[8],
                    (list(row[0]))[9],
                    (list(row[0]))[10],
                    (list(row[0]))[11],
                    (list(row[0]))[4],
                    (list(row[0]))[7],
                    (list(row[0]))[5],
                    datetime.now(),
                    SesionKey
            ]
            cursor.execute(prices_insert_sql, tuple(prices_insert_output))
            cursor.commit()
        print('DB Updated CPP....!!!!')

    except Exception as e:
        errorMessage = str(e)
        print('ERR',errorMessage)
        metal_utils.updateException(competitorId,SesionKey,errorMessage)
