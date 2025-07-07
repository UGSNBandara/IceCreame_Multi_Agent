import mariadb
from CRUD.db import get_db_connection 
from CRUD.help import convert_unserializable_types_for_json

async def get_icecream_by_id (ice_creame_id: int) -> dict | None:
    """Get the ice cream by id"""
    async with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM ice_creame WHERE product_id = (?)", (ice_creame_id,))
            ice_cream = cursor.fetchone()
            return convert_unserializable_types_for_json(ice_cream) if ice_cream else None
        except mariadb.Error as e:
            print(f"CRUD: Error retriving icecream by producti id : {e}")
            return {"state" : "error", "error" : e}
        finally:
            if cursor:
                cursor.close()
                
async def get_icecream_by_flavour (flavout: str) -> list[dict]|dict:
    """Get the ice cream by flavor"""
    
    async with get_db_connection() as conn:
        cursor = None
        try: 
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM ice_creame WHERE flavor = (?)", (flavout,))
            ice_creams = cursor.fetchall()
            return convert_unserializable_types_for_json(ice_creams) if ice_creams else []
        except mariadb.Error as e:
            print(f"CURD : Error retriving ice cream by the flovor : {e}")
            return {"state" : "error", "error" : e}
        finally:
            if cursor:
                cursor.close()