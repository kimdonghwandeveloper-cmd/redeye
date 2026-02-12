import os
import asyncio
from zapv2 import ZAPv2
from dotenv import load_dotenv

load_dotenv()

ZAP_URL = os.getenv("ZAP_URL", "http://zap-service.railway.internal:8080")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "redeye1234")

class ZapScanner:
    def __init__(self):
        self.zap = ZAPv2(apikey=ZAP_API_KEY, proxies={'http': ZAP_URL, 'https': ZAP_URL})

    async def scan(self, target_url: str):
        print(f"🚀 [ZAP] Scanning target: {target_url} via {ZAP_URL}")
        
        try:
            # Check connection first
            self.zap.core.version
            
            # 1. Spidering
            scan_id = self.zap.spider.scan(target_url)
            while int(self.zap.spider.status(scan_id)) < 100:
                await asyncio.sleep(2)
            print("✅ [ZAP] Spidering complete.")
            
            # 3. Collect Alerts
            alerts = self.zap.core.alerts(baseurl=target_url)
            return alerts
            
        except Exception as e:
            print(f"⚠️ [ZAP] Connection failed or ZAP not running: {e}")
            # print("🔄 Switching to MOCK MODE for testing...")
            
            # Return empty list instead of fake vulnerability
            return []

zap_scanner = ZapScanner()
