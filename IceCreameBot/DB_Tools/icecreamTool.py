from CRUD.icecreamCrud import get_icecream_by_id

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