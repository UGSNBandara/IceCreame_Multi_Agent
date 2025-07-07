# crud.py
import mariadb
from CRUD.db import get_db_connection 
from CRUD.help import convert_unserializable_types_for_json
import asyncio

async def add_order_db(customer_id: int, type: str, address_table: str, telepone_num: str, order_des:str, amount: float) -> dict:
    """Adds a new order to the 'orders' table and returns its ID."""
    async with get_db_connection() as conn: 
        cursor = None
        order_id = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO orders (amount, customer_id, type, address_table, telepone_num, oder_des) VALUES (?, ?, ?, ?, ?, ?)",
                (amount, customer_id, type, address_table, telepone_num, order_des,)
            )
            conn.commit()
            order_id = cursor.lastrowid
            print(f"CRUD: Order added successfully with ID: {order_id}")
            return {
                "status" : 200,
                "id" : order_id,
            }
        except mariadb.Error as e:
            conn.rollback()
            print(f"CRUD: Error adding order: {e}")
            return {
                "status" : 404,
                "error" : e,
            }
        finally:
            if cursor:
                cursor.close()



async def get_order_by_id(order_id: int) -> dict:
    """Retrieves oder details by the id"""
    async with get_db_connection() as conn:
        cursor = None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM orders WHERE order_id = (?)", (order_id,))
            order = cursor.fetchone()
            return convert_unserializable_types_for_json(order) if order else {}
        except mariadb.Error as e:
            print(f"CRUD: Error retrieving order by order id: {e}")
            return {
                "status" : 404,
                "error" : e
            }
        finally:
            if cursor:
                cursor.close()

async def change_the_order_state(state: str, order_id: int) -> dict:
    """Change the order state as complete"""
    async with get_db_connection() as conn:
        cursor = None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("UPDATE orders SET order_status = (?) WHERE order_id = (?)", (state, order_id,))
            conn.commit()
            cursor.execute("SELECT * FROM orders WHERE order_id = (?)", (order_id,))
            order = cursor.fetchone()
            return convert_unserializable_types_for_json(order) if order else {}
        except mariadb.Error as e:
            print(f"Order CURD: Error changing the state of the order: {e}")
            return {
                "status" : 404,
                "error" : e,
            }
        finally:
            if cursor:
                cursor.close()
                

async def get_order_by_customer_id(customer_id: int) -> list[dict]|dict:
    """Retrieves oder details by the id"""
    async with get_db_connection() as conn:
        cursor = None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM orders WHERE customer_id = (?)", (customer_id,))
            orders = cursor.fetchall()
            return convert_unserializable_types_for_json(orders) if orders else []
        except mariadb.Error as e:
            print(f"CRUD: Error retrieving order by order id: {e}")
            return {"status" : 404,
                    "error" : e,
                    }
        finally:
            if cursor:
                cursor.close()
