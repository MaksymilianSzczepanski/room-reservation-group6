"""Create the current service's PostgreSQL schema before Django migrations."""
import os

import psycopg2
from psycopg2 import sql

from microservices.settings import SERVICE_NAME

connection = psycopg2.connect(
    dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"], password=os.environ["DB_PASS"],
    host=os.environ.get("DB_HOST", "db"), port=os.environ.get("DB_PORT", "5432"),
)
connection.autocommit = True
with connection.cursor() as cursor:
    cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SERVICE_NAME)))
connection.close()
