# db_connection.py
import mysql.connector
import yaml
import os
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

class MySQLConnection:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        self.conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            auth_plugin='caching_sha2_password'
        )
        self.cursor = self.conn.cursor(dictionary=True)
    
    def execute(self, query, params=None):
        """
        Executes raw SQL. 
        `query` is a string, `params` is a tuple or dict (optional).
        """
        self.cursor.execute(query, params or ())
        return self.cursor
    
    def commit(self):
        self.conn.commit()
    
    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def load_queries(query_file_path="queries.yaml"):
    with open(query_file_path, "r") as f:
        data = yaml.safe_load(f)
    return data
