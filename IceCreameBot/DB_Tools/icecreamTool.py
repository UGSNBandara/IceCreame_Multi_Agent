from CRUD.icecreamCrud import get_icecream_by_id, get_icecream_by_flavour

async def get_product_details_by_product_id(product_id:  int) -> dict:
    """to get the product detils of ice cream by its product ID

    Args:
        product_id (int): product id

    Returns:
        dict: if success dict contain ice cream details, if erro contain error details
    """
    response = await get_icecream_by_id(ice_creame_id=product_id)
    if response:
        return response
    return {
        "state" : "No ice cream product found by this ID",
    }
    
    
async def get_ice_creams_by_flavor_id(category_id: int) -> list[dict]|dict:
    """to get the ice crreams by the flavor ID ( Category ID )

    Args:
        category_id (int): id of the category need to get ice creams

    Returns:
        list[dict]|dict: list of the ice creams dictonaries in the given flavor, and if error occured error will be retured as dict
    """
    
    response = await get_icecream_by_flavour(flavour=category_id)
    if response:
        return response
    return {
        "error" : "No output got from this function",
    }
    