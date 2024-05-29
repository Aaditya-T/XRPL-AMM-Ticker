import aiosqlite
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AMMInfo
from xrpl.utils import drops_to_xrp
import json

JSON_RPC_URL = "https://s1.ripple.com:51234/"
client = JsonRpcClient(JSON_RPC_URL)

def hexToStr(hex_str):
        bytes_object = bytes.fromhex(hex_str)
        readable_str = bytes_object.decode('utf-8')
        readable_str = readable_str.replace('\x00', '')
        return readable_str
    
def formateValue(number):
    try:
        number = float(number)
    except ValueError:
        return "Invalid number"

    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}m"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}k"
    else:
        return str(number)
    
def ProcessedData(data):
    retData = []
    if len(data['amm']['amount2']['currency']) > 3:
        retData.append(f"{hexToStr(data['amm']['amount2']['currency'])} - {formateValue(data['amm']['amount2']['value'])}")
    else:
        retData.append(f"{data['amm']['amount2']['currency']} - {formateValue(data['amm']['amount2']['value'])}")
    retData.append(f"XRP - {formateValue(drops_to_xrp(data['amm']['amount']))}")
    retData.append(f"lp - {formateValue(data['amm']['lp_token']['value'])}")
    retData.append(f"fee - {(data['amm']['trading_fee']/1000)} %")
    retData.append(data['amm']['account'])
    
    return retData

def getAMMInfo(acc : str):
    playload = AMMInfo(amm_account=acc)
    response = client.request(playload)
    return response.result

#Database opreations

async def deleteTableData(database, table):
    async with aiosqlite.connect(database) as db:
        cursor = await db.cursor()
        await cursor.execute(f"DELETE FROM {table}")
        await db.commit()
        
async def insert_pool_data(poolstring , address):
    async with aiosqlite.connect("database.db") as db:
        async with db.cursor() as cursor:
            await cursor.execute('''
            INSERT INTO pools (poolString, Account)
            VALUES (?, ?)
        ''', (poolstring, address))
            await db.commit()
        
async def fetchdata(database , table):
    async with aiosqlite.connect(database) as db:
        async with db.execute(f'SELECT * FROM {table}') as cursor:
            return await cursor.fetchall()
        
async def getAddress(poolString):
    try : 
        async with aiosqlite.connect("database.db") as db:
            async with db.execute(f'select Account from pools where poolString like ? || ? || ?', ('%', poolString, '%')) as cursor:
                return await cursor.fetchall()
    except:
        return False
    
async def insertCategoryData(server_id, category_id, curr1, curr2, lp, fee , accAdd):
    async with aiosqlite.connect("database.db") as db:
        async with db.cursor() as cursor:
            insert_query = """
                INSERT INTO CategoryData (server_id, category_id, curr1, curr2, lp, fee , accAdd)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            try:
                await cursor.execute(insert_query, (server_id, category_id, curr1, curr2, lp, fee , accAdd))
                await db.commit()
            except aiosqlite.Error as e:
                print(f"Error inserting data: {e}")

async def deleteCategoryData(db_path, table_name, condition):
    column, value = list(condition.items())[0]
    async with aiosqlite.connect(db_path) as db:
        await db.execute(f"DELETE FROM {table_name} WHERE {column} = ?", (value,))
        await db.commit()

async def getCategoryId(db_path, table_name, condition ):
    column, value = list(condition.items())[0]
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(f"SELECT category_id FROM {table_name} WHERE {column} = ?", (value, )) as cursor:
            return await cursor.fetchone()

async def getaccAdd():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT DISTINCT accAdd FROM CategoryData") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
        

async def UpdateCategoryData(accAdd, curr1, curr2, lp, fee):
    async with aiosqlite.connect("database.db") as db:
        async with db.cursor() as cursor:
            query = """
            UPDATE CategoryData
            SET curr1 = ?, curr2 = ?, lp = ?, fee = ?
            WHERE accAdd = ?
            """
            await cursor.execute(query, (curr1, curr2, lp, fee, accAdd))
            await db.commit()
    

if __name__ == "__main__":
    pass