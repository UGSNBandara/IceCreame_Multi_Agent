from typing import Optional
from CRUD.complainCrud import add_complain_db, get_complain_by_complain_id, get_complains_by_order_id

async def add_complain(order_id: int, description: str, expected_resolution: Optional[str]) -> dict:
    """to add a complain to the db

    Args:
        order_id (int): id of the order going to complain
        description (str): small description about the compalin
        expected_resolution (Optional[str]): expected resolution by the customer, this is optional if customer expect nothin put as None

    Returns:
        dict: dictionary contain the state of the operation. either success or error
    """
    response = await add_complain_db(order_id=order_id, description=description, expected_resolution=expected_resolution)
    if response:
        return {
            "state" : "success",
            "complain_id" : response,
        }
    else:
        return {
        "state" : "error_occured",
        }


async def get_complain_by_complainid(complain_id: int) -> dict:
    """To get the complain by complain ID

    Args:
        complain_id (int): complain Id

    Returns:
        dict: response, if success the complain dict, otherwise error dict
    """
    
    response = await get_complain_by_complain_id(complain_id=complain_id)
    if response:
        return response
    
    return {
        "state" : "No complain found by this complain id"
    }
    

async def get_complain_by_orderid(order_id: int) -> list[dict]|dict:
    """to get the complains for a order by order Id

    Args:
        order_id (int): order id

    Returns:
        list[dict]|dict: list of dict if complains retrived correctly, if no complain empty list. if error occured dictionary which contain the error
    """
    response = await get_complains_by_order_id(order_id=order_id)
    if response:
        return response

    return {
        "state" : "No complain found by this order id"
    }