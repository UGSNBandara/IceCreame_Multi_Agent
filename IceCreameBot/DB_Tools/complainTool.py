from typing import Optional
from CRUD.complainCrud import add_complain


async def add_complain_to_db(description: str) -> dict:
    """to add the complain to the database

    Args:
        description (str): description of the complain

    Returns:
        dict: result of the operation. if succeede retun the id of the complain. 
    """
    desc = (description or "").strip()
    if not desc:
        return {"state": "error_occured", "error": "description_empty"}
    try:
        new_id = await add_complain(desc)
        return {"state": "success", "complain_id": int(new_id)}
    except Exception as err:
        return {"state": "error_occured", "error":"Error occured, please try again later or contact support."}
