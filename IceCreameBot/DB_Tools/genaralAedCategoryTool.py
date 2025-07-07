from CRUD.genaral_aed_catory_icecream import get_aed_categories_by_age_group, get_aed_categories_by_emotion, get_aed_categories_by_emotion_and_agegroup


async def get_icecream_suggestion_by_age_group (age_group: str) -> list[dict]|dict:
    """to get the ice creams based on the age group 

    Args:
        age_group (str): age group , should be one of the : ['children','teen','young adult','adult','senior']

    Returns:
        list[dict]|dict: if success return a list of dictionary which contained 
        suggestions based on age group if fail will get empty dict or dict containing error
    """
    response = await get_aed_categories_by_age_group(age_group=age_group)
    if response:
        return response
    return {
        "state" : "No ice cream found under this category",
    }
    
async def get_icecream_suggestion_by_emotion (emotion: str) -> list[dict]|dict:
    """to get the creams based on the emotion

    Args:
        emotion (str): emotion type, should be one of the : ['happiness','sadness','anger','surprise','fear','disgust']

    Returns:
        list[dict]|dict: if success return a list of dictionary which contained 
        suggestions based on emotion type if fail will get empty dict or dict containing error
    """
    response = await get_aed_categories_by_emotion(emotion=emotion)
    if response:
        return response
    return {
        "state" : "No ice cream found under this category",
    }


async def get_icecream_suggestion_by_emotion_plus_age_group(age_group: str, emotion: str) -> list[dict] | dict:
    """to get the ice creams based on the both emotion adn age group

    Args:
        age_group (str): age group , should be one of the : ['children','teen','young adult','adult','senior']
        emotion (str): emotion type, should be one of the : ['happiness','sadness','anger','surprise','fear','disgust']

    Returns:
        list[dict] | dict: if success return a list of dictionary which contained 
        suggestions based on emotion type if fail will get empty dict or dict containing error
    """
    response = await get_aed_categories_by_emotion_and_agegroup(emotion=emotion, age_group=age_group)
    if response:
        return response
    return {
        "state" : "No ice cream found under this category",
    }