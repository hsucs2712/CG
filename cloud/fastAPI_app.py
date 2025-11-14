from fastapi import FastAPI


app = FastAPI(
    title="CGTtest API",
    description= "API for GPU Burn and Device Management",
    version= "1.0"
)

# 資料模型
class DeviceInfo(BaseModel):
    device_id: str
    cpu: str
    ram: str
    gpu: str
    disk: str
    os: str
    ip_address: Optional[str] = None

class TestRequest(BaseModel):
    device_id: str
    product_id: str
    test_duration: int  # 測試時長(分鐘)
    test_params: Optional[dict] = {}

class TestResult(BaseModel):
    device_id: str
    product_id: str
    test_id: str
    status: str  # running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result_data: Optional[dict] = {}

@app.get("/")
def read_root():
    return {
        "message": "雲端測試系統 API",
        "version": "1.0",
        "endpoints": {
            "ping":"/ping",
            "register": "/device/register",
            "test_request": "/test/request",
            "test_start": "/test/start",
            "test_complete": "/test/complete",
            "devices": "/devices",
            "tests": "/tests"
            }
    }

@app.post("")

@app.get("/ping")
def ping():
    return {"status":"ok","message":"ping"}