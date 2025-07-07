# tools.py
from typing import Optional
from CRUD.OrderCrud import add_order_db, get_order_by_id, get_order_by_customer_id, change_the_order_state

async def add_order_tool(customer_id: Optional[int], type: str, address_table: Optional[str], telepone_num: Optional[str], order_des:str, amount: float) -> dict:
    """To add new oder to Database

    Args:
        customer_id (Optional[int]): customer id of the customer, this could be null when odering in guest mood
        type (str): ['dine-in','takeaway','delivery'] only could be one of this.
        address_table (Optional[str]): for dine-in type : table code, for delivery type : address and for takeaway type this should be null
        telepone_num (Optional[str]): for delivery and takeaway telepone number is requied but for dine-in not required so can be null
        order_des (str): description of oder as a list of dictionary ex: [{'Code": 5, "count": 5}, {"Code":6, "Count": 8}] as a string to store in db 
        amount (float): total amount of the order

    Returns:
        dict: output as a dictionary
    """
    response = await add_order_db(customer_id, type, address_table, telepone_num, order_des, amount)
    return response


async def get_order_by_order_tool(order_id: int) -> dict:
    """Retrive the specific order by order Id

    Args:
        order_id (int): order Id

    Returns:
        dict: oder dictionary if error occured will return also dic contain error
    """
    response = await get_order_by_id(order_id=order_id) 
    if response:
        return response
    return{
        "state" : "No order found by this order id"
    }


async def get_orders_by_customer_id_tool(customer_id: int) -> list[dict]|dict:
    """to get the all oders placed by the cutomer by customer id

    Args:
        customer_id (int): customer id

    Returns:
        list[dict]|dict: if availble will retunr list of dicitonary other wise will return erro dictionary which contain the error.
    """
    response = await get_order_by_customer_id(customer_id=customer_id) 
    if response:
        return response
    return{
        "state" : "No order found by this customer id"
    }


async def change_state_of_order(order_id: int, state: str) -> dict:
    """To change the state of the order

    Args:
        order_id (int): id of the order 
        state (str): state of the order, input should be only one of this : ['Pending','Preparing','On the Way','Delivered','Cancelled']

    Returns:
        dict: if success return order dict, other wise error dict
    """
    response = await change_the_order_state(state=state, order_id=order_id)
    if response:
        return response
    
    return{
        "state" : "No order found by order id"
    }