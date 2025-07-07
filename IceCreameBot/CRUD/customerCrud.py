import mariadb
from CRUD.db import get_db_connection 
from CRUD.help import convert_unserializable_types_for_json
import asyncio


async def add_customer_db(customer_username: str, telepone_num: str, address: str) -> dict:
    """Adds a new customer to the customers table"""
    async with get_db_connection() as conn: 
        cursor = None
        order_id = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO customers (customer_username, telepone_num, address) VALUES (?, ?, ?)",
                (customer_username, telepone_num, address,)
            )
            conn.commit()
            customer_id = cursor.lastrowid
            print(f"CRUD: customer added successfully with ID: {customer_id}")
            return {
                "status" : "successfully added the customer",
                "id" : customer_id,
            }
        except mariadb.Error as e:
            conn.rollback()
            print(f"CRUD: Error adding customer: {e}")
            return {
                "status" : "Fail to add the order",
            }
        finally:
            if cursor:
                cursor.close()

async def get_customer_by_id(customer_id: int) -> dict | None:
    """Retrieves customer details by the id"""
    async with get_db_connection() as conn:
        cursor = None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM customers WHERE customer_id = (?)", (customer_id,))
            customer = cursor.fetchone()
            return convert_unserializable_types_for_json(customer) if customer else None
        except mariadb.Error as e:
            print(f"CRUD: Error retrieving order by id: {e}")
            return {
                "state" : 404,
                "error" : e,
            }
        finally:
            if cursor:
                cursor.close()

async def get_customer_by_telepone_num(telepone_num: str) -> dict | None:
    """Retrieves customer details by the telepone number"""
    async with get_db_connection() as conn:
        cursor = None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM customers WHERE telepone_num = (?)", (telepone_num,))
            customer = cursor.fetchone()
            return convert_unserializable_types_for_json(customer) if customer else None
        except mariadb.Error as e:
            print(f"CRUD: Error retrieving order by telepone num: {e}")
            return {
                "error" : e
            }
        finally:
            if cursor:
                cursor.close()
                
