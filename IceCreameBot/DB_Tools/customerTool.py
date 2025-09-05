# DB_Tools/customerTool.py

from typing import Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
from CRUD.customerCrud import (
    add_customer as add_customer_db,
    get_customer_by_phone as get_customer_by_phone_db,
    update_customer as update_customer_db,
)

async def add_customer(customer_username: str, telepone_num: Optional[str], address: Optional[str]) -> Dict[str, Any]:
    """
    To add a new customer to the system

    Args:
        customer_username (str): customer username
        telepone_num (str): Customer telepone number, not requier but if user give add other wise enter None
        address (Optional[str]): customer address also not requier but if user gives add other wise enetr None

    Returns:
        dict: if success , dic with user id and success state, if error , dic conatining error
    """
    try:
        row = await add_customer_db(name=customer_username, phone=telepone_num, address=address)
        # Return a stable, agent-friendly shape
        return {
            "state": "success",
            "customer": row,          # includes: id, name, phone, address
        }
    except IntegrityError:
        return {"state": "error_occured", "error": "phone_already_exists"}
    except Exception:
        return {"state": "error_occured", "error": "db_error"}


async def get_customer_by_tel_num(telepone_num: str) -> Dict[str, Any]:
    """to get the customer details by telepone number
    Args:
        telepone_num (str): telepone number
    Returns:
        dict: id user is present dict contain coustomer details, if error occured erro
    """
    row = await get_customer_by_phone_db(phone=telepone_num)
    if row:
        return row  # JSON-safe dict: {id, name, phone, address}
    return {
        "state": "No customer found by this number"
    }


async def update_customer_tool(
    customer_id: int,
    customer_username: Optional[str] = None,
    telepone_num: Optional[str] = None,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update existing customer fields. Provide only the fields you want to change.
    Returns {'state':'success','customer':{...}} or an error state.
    """
    try:
        row = await update_customer_db(
            customer_id=customer_id,
            name=customer_username,
            phone=telepone_num,
            address=address,
        )
        if row is None:
            return {"state": "error_occured", "error": "customer_not_found"}
        return {"state": "success", "customer": row}
    except IntegrityError:
        return {"state": "error_occured", "error": "phone_already_exists"}
    except Exception:
        return {"state": "error_occured", "error": "db_error"}
