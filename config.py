import os
from dotenv import load_dotenv

load_dotenv()   # .env 파일을 읽어서 환경변수로 등록

DB_CONFIG = {
    'host':     os.getenv('DB_HOST',     'localhost'),
    'user':     os.getenv('DB_USER',     'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME',     'mydb'),
    'charset':  'utf8',
}