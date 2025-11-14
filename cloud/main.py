from fastAPI_app import app
import mongoDB
import uvicorn



if __name__ == "__main__" :
    try:
        print("connect to MongoDB... ")
        mongoDB.connect2mongodb()

        print("Start FastAPI server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        print("FastAPI啟動失敗:", e)
    finally:
        mongoDB.disconnect()