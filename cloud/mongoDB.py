from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from datetime import datetime
import os

client = MongoClient('mongodb://localhost:27017/')
db = client['CGTest']
collection = db['devices'] 

# app = FastAPI()

def connect2mongodb():
    client = MongoClient('mongodb://localhost:27017/')
    db = client['CGTest']
    print("connected 2 mongodb")

def disconnect():
    if client:
        client.close()
        print("Disconnected")

def test_connect():
    try:
        client.server_info()
        print("成功...")
    except Exception as e:
        raise Exception("無法連線", e)



