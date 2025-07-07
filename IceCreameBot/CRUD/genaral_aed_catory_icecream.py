import mariadb
from CRUD.db import get_db_connection
from CRUD.help import convert_decimals_for_json

async def get_aed_categories_by_age_group (age_group: str) -> list[dict]|dict:
    """Get ice creams according to the age group"""
    async with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM genaral_aed_category WHERE age_group= (?)", (age_group,))
            ice_creams = cursor.fetchall()
            return convert_decimals_for_json(ice_creams) if ice_creams else []
        except mariadb.Error as e:
            print(f"CRUD: Error retriving icecreams by agegroup : {e}")
            return {"state" : "error", "error" : e}
        finally:
            if cursor:
                cursor.close()
                
async def get_aed_categories_by_emotion (emotion: str) -> list[dict]|dict:
    """Get ice creams according to the emotion"""
    async with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM genaral_aed_category WHERE emotion= (?)", (emotion,))
            ice_creams = cursor.fetchall()
            return convert_decimals_for_json(ice_creams) if ice_creams else []
        except mariadb.Error as e:
            print(f"CRUD: Error retriving icecreams by emotion : {e}")
            return {"state" : "error", "error" : e}
        finally:
            if cursor:
                cursor.close()

async def get_aed_categories_by_emotion_and_agegroup (emotion: str, age_group: str) -> list[dict]|dict:
    """Get ice creams according to both emotion and age_group"""
    async with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM genaral_aed_category WHERE emotion= (?) AND age_group = (?)", (emotion, age_group,))
            ice_creams = cursor.fetchall()
            return convert_decimals_for_json(ice_creams) if ice_creams else []
        except mariadb.Error as e:
            print(f"CRUD: Error retriving icecreams by emotion and age_group : {e}")
            return {"state" : "error", "error" : e}
        finally:
            if cursor:
                cursor.close()
