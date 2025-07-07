from CRUD.customerCrud import add_customer_db, get_customer_by_id, get_customer_by_telepone_num
from typing import Optional


async def add_customer(customer_username: str, telepone_num: Optional[str], address: Optional[str]) -> dict:
    """To add a new  customer to the system

    Args:
        customer_username (str): customer username
        telepone_num (str): Customer telepone number, not requier but if user give add other wise enter None
        address (Optional[str]): customer address also not requier but if user gives add other wise enetr None

    Returns:
        dict: if success , dic with user id and success state, if error , dic conatining error
    """
    
    response = await add_customer_db(customer_username=customer_username, telepone_num=telepone_num, address=address)
    return response

async def get_customer_by_Id(customer_id: int) -> dict:
    """to get the customer details by customer id

    Args:
        customer_id (int): customer id

    Returns:
        dict: if success, return dic wich contain customer details, if error, return dict conaining error
    """
    response = await get_customer_by_Id(customer_id=customer_id)
    if response:
        return response
    return {
        "state" : "No customer found by this Id"
    }

async def get_customer_by_tel_num(telepone_num: str) -> dict:
    """to get the customer details by telepone number

    Args:
        telepone_num (str): telepone number

    Returns:
        dict: id user is present dict contain coustomer details, if error occured erro
    """
    response = await get_customer_by_telepone_num(telepone_num=telepone_num)
    if response:
        return response
    return {
        "state" : "No customer found by this number"
    }