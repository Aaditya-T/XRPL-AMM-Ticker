import requests
import helpers
import aiohttp
import asyncio
import threading
from xrpl.utils import drops_to_xrp
import time

DB_PATH = "database.db"

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.json()
    
async def process_data(data):
    await helpers.deleteTableData(DB_PATH, "pools")
    for entry in data:
        account_number = entry["Account"]
        asset_info = {
            "asset": entry["Asset"],
            "asset2": entry["Asset2"]
        }
        
        if len(asset_info["asset2"]["currency"]) > 3:
            asset_info["asset2"]["currency"] = helpers.hexToStr(asset_info["asset2"]["currency"])
        else:
            asset_info["asset2"]["currency"] = asset_info["asset2"]["currency"]
        if len(asset_info["asset"]["currency"]) > 3:
            asset_info["asset"]["currency"] = helpers.hexToStr(asset_info["asset"]["currency"])
        else:
            asset_info["asset"]["currency"] = asset_info["asset"]["currency"]
        
        pool_string = f"{asset_info['asset']['currency']}/{asset_info['asset2']['currency']}.{asset_info['asset2']['issuer']}"
        await helpers.insert_pool_data(f"{pool_string}", f"{account_number}")
        
async def UpdatePoolStrings():
    url = "https://api.xrpscan.com/api/v1/amm/pools"
    resp = requests.get(url)
    data = resp.json()
    await process_data(data)

async def UpdateCategoryData():
    ls = await helpers.getaccAdd()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, f'https://api.xrpscan.com/api/v1/amm/{val}') for val in ls]
        try:
            results = await asyncio.gather(*tasks)
            for data in results:
                if len(data['amount2']['currency']) > 3:
                    await helpers.UpdateCategoryData(data['account'],f"{helpers.hexToStr(data['amount2']['currency'])} - {helpers.formateValue(data['amount2']['value'])}" ,f"XRP - {helpers.formateValue(drops_to_xrp(data['amount']))}",f"lp - {helpers.formateValue(data['lp_token']['value'])}",f"fee - {(data['trading_fee']/1000)} %")
                else:
                    await helpers.UpdateCategoryData(data['account'],f"{data['amount2']['currency']} - {helpers.formateValue(data['amount2']['value'])}" ,f"XRP - {helpers.formateValue(drops_to_xrp(data['amount']))}",f"lp - {helpers.formateValue(data['lp_token']['value'])}",f"fee - {(data['trading_fee']/1000)} %")
        except Exception as e:
            print(f'Error fetching data: {e}')

def run_in_thread(func):
    def wrapper():
        print(f"Thread {threading.current_thread().name} has started running.")
        asyncio.run(func())
    return wrapper


async def main():
    print('Starts')
    thread1 = threading.Thread(target=run_in_thread(UpdatePoolStrings))
    thread2 = threading.Thread(target=run_in_thread(UpdateCategoryData))
    thread1.start()
    thread2.start()
    
    thread1.join()
    thread2.join()
    print('ends')    

while True:
    asyncio.run(main())
    time.sleep(600 * 3) # 30 minutes

