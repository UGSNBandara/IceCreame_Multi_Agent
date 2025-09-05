# DB_Tools/orderTool.py
from typing import List, Dict, Optional, Any
from CRUD.OrderCrud import add_order as add_order_db, get_order_by_id as get_order_by_id_db

async def add_order(
    customer_id: Optional[int],
    items: List[Dict[str, Any]],
    dine_in: bool,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    table_number: Optional[int] = None,
) -> Dict[str, Any]:
    """to add a new order

    Args:
        customer_id (int): id of the customer placing the order
        items (List[Dict[str, Any]]): order items as a list of dictionaries (will be saved as json)
        dine_in (bool): True for dine-in, False for take-away
        address (Optional[str]): delivery address (for take-away; optional)
        phone (Optional[str]): customer phone (optional)
        table_number (Optional[int]): table number (for dine-in; optional)

    Returns:
        dict: created order dictionary on success.
              if error occurred returns {"state":"error_occured","error":"db_error"}
    """
    try:
        row = await add_order_db(
            customer_id=customer_id,
            items=items,
            dine_in=dine_in,
            address=address,
            phone=phone,
            table_number=table_number,
        )
        return row
    except Exception:
        return {"state": "error_occured", "error": "db_error"}


async def get_order_by_id(order_id: int) -> Dict[str, Any]:
    """to get the order details by order id

    Args:
        order_id (int): id of the order

    Returns:
        dict: order dictionary if present.
              if not found returns {"state":"not_found"}
              if error occurred returns {"state":"error_occured","error":"db_error"}
    """
    try:
        row = await get_order_by_id_db(order_id)
        return row if row else {"state": "not_found"}
    except Exception:
        return {"state": "error_occured", "error": "db_error"}
