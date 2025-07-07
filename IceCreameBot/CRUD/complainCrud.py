# crud.py
import mariadb
from CRUD.db import get_db_connection
from CRUD.help import convert_unserializable_types_for_json

async def add_complain_db(order_id: int, description: str, expected_resolution: str | None = None) -> int | None:
    """Adds a complaint to the 'complains' table for a given order."""
    async with get_db_connection() as conn:
        cursor = None
        complain_id = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO complains (description, expected_resolution, order_id) VALUES (?, ?, ?)",
                (description, expected_resolution, order_id,)
            )
            conn.commit()
            complain_id = cursor.lastrowid
            print(f"CRUD: Complaint added successfully for order ID {order_id} with complaint ID: {complain_id}")
        except mariadb.Error as e:
            conn.rollback()
            print(f"CRUD: Error adding complaint: {e}")
        finally:
            if cursor:
                cursor.close()
    return complain_id

async def get_complain_by_complain_id(complain_id : int) -> dict:
    """Return the complain data of specified id"""
    
    async with get_db_connection() as conn:
        cursor = None
        try:
           cursor = conn.cursor(dictionary=True)
           cursor.execute("SELECT complai_id, description,  expected_resolution, complain_date, order_id FROM complains WHERE complai_id = (?)", (complain_id,))
           complain = cursor.fetchone()
           return convert_unserializable_types_for_json(complain)
        except mariadb.Error as e:
            print(f"CURD : error retriving complain by complai id : {e}")
            return {"status": 404, "error" : e,}
        finally: 
            if cursor:
                cursor.close()
                
                
async def get_complains_by_order_id(order_id : int) -> list[dict]|dict:
    """Return the complains data of on specified oder"""
    
    async with get_db_connection() as conn:
        cursor = None
        try:
           cursor = conn.cursor(dictionary=True)
           cursor.execute("SELECT * FROM complains WHERE order_id = (?)", (order_id,))
           complain = cursor.fetchall()
           return convert_unserializable_types_for_json(complain)
        except mariadb.Error as e:
            print(f"CURD : error retriving complains by order_id : {e}")
            return {
                    "status" : 404,
                    "error" : e,
                    }
        finally: 
            if cursor:
                cursor.close()