# config.py
import os
import yaml

config = yaml.safe_load(open("config.yaml"))

DB_HOST = config["DB_HOST"]
DB_USER = config["DB_USER"]
DB_PASSWORD = config["DB_PASSWORD"]
DB_NAME = config["DB_NAME"]

# For BM25 default parameters
K1 = config["K1"]
B = config["B"]

# Path to queries.yaml
cwd = os.getcwd()

# Path to queries.yaml
QUERY_FILE = os.path.join(cwd, "queries.yaml")

# Path to datasets
DATASET_DIR = os.path.join(cwd, "datasets")