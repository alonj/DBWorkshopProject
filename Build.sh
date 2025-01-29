#!/usr/bin/env bash

# Biorxiv dataset file url variable
BIORXIV_DATASET_FILE_URL="https://huggingface.co/datasets/mteb/biorxiv-clustering-p2p/resolve/main/test.jsonl.gz"
# Medrxiv dataset file url variable
MEDRXIV_DATASET_FILE_URL="https://huggingface.co/datasets/mteb/medrxiv-clustering-p2p/resolve/main/test.jsonl.gz"

# Download files and unzip

# create dir for dataset files
mkdir -p datasets

# check if file exists
if [ -f "datasets/biorxiv.jsonl" ]; then
    echo "File already exists"
else
    echo "File does not exist"
    wget $BIORXIV_DATASET_FILE_URL
    # unzip to "biorxiv"
    gunzip test.jsonl.gz
    mv test.jsonl datasets/biorxiv.jsonl
fi

# check if the file was successfully downloaded
if [ -f "datasets/biorxiv.jsonl" ]; then
    echo "File downloaded successfully"
else
    echo "File download failed"
fi

# check if file exists
if [ -f "datasets/medrxiv.jsonl" ]; then
    echo "File already exists"
else
    echo "File does not exist"
    wget $MEDRXIV_DATASET_FILE_URL
    # unzip to "medrxiv"
    gunzip test.jsonl.gz
    mv test.jsonl datasets/medrxiv.jsonl
fi

# check if the file was successfully downloaded
if [ -f "datasets/medrxiv.jsonl" ]; then
    echo "File downloaded successfully"
else
    echo "File download failed"
fi

# Create virtual environment
if [ -d "medicaldb" ]; then
    echo "Virtual environment already exists"
else
    python3 -m venv medicaldb
fi

# Check if virtual environment was created successfully
if [ -d "medicaldb" ]; then
    echo "Virtual environment created successfully"
else
    echo "Virtual environment creation failed"
fi

# Activate virtual environment
source medicaldb/bin/activate

# Install dependencies
pip install -r requirements.txt -qq

# Check if dependencies were installed successfully
if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully"
else
    echo "Dependencies installation failed"
fi

# Create MySQL database from "create_db.sql"
mysql -u root -p < init_db.sql

# Check if database was created successfully
if [ $? -eq 0 ]; then
    echo "Database created successfully"
else
    echo "Database creation failed"
fi

# check if --build_and_run flag is set
if [ "$1" == "--build_and_run" ]; then
    python app.py
fi