import pyodbc

# Random delay for each product page requests
MIN_SECONDS_DELAY = 1
MAX_SECONDS_DELAY = 1

# Limit running crawler per dealer
MAX_RUNNING_CRAWLER_PER_DEALER = 1

# Number of days use to calculate lowest premium average
AVERAGE_PREMIUM_DAYS_COVER = 30

# Percentage to be discounted for average premium
AVERAGE_PREMIUM_MINIMUM_DISCOUNT_PERCENTAGE = 6

# SMTP GMAIL credentials
SMTP_GMAIL_USERNAME = 'boldpreciousmetals123@gmail.com'
SMTP_GMAIL_PASSWORD = 'ash@2011'

#RECEIVER_LISIT = "sachin.shinde@realizertech.com,newsachins@gmail.com,bhagyashri.salgare@realizertech.com,chittaranjanmore96@gmail.com"

# Premium Notification schedule time
PREMIUM_NOTIFICATION_SCHEDULE = '12:00'

DATABASE_BACKUP_SCHEDULE = '10:00'

SEND_ERRORS_VIA_EMAIL = True

#DB_CONNECTION = pyodbc.connect('DRIVER={SQL Server};SERVER=106.201.231.27;DATABASE=BMProd;UID=sa;PWD=ash@2011')

# DB_CONNECTION = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=172.106.161.81;DATABASE=BBDProd;UID=sa;PWD=Ash@2011$D;')



DB_CONNECTION = pyodbc.connect('DRIVER={SQL Server};SERVER=198.71.61.63;DATABASE=BMProd;UID=sa;PWD=BMPwd@2023')
# DB_CONNECTION = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER=172.106.161.81;DATABASE=BBDTempDB;UID=sa;PWD=Ash@2011$D;')
# conn = pyodbc.connect("DRIVER={ODBC Driver 11 for SQL Server};SERVER=169.54.250.80,6047;DATABASE=BrandProtect;UID=jborden;PWD=sha45549;Trusted_Connection=yes;")

DRIVER_PATH = "C:\\chromedriver-win64\\chromedriver-win64\chromedriver.exe"