import datetime
from decimal import Decimal

def convert_unserializable_types_for_json(obj):
    """
    Recursively converts Decimal, datetime, and timedelta objects to JSON-serializable types.
    """
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat() # e.g., '2025-07-07' or '2025-07-07T18:10:22.123456'

    elif isinstance(obj, datetime.timedelta):
        # Convert timedelta to total seconds (float). This is usually the most useful.
        return obj.total_seconds()
        # Alternatively, to convert to a string like '1 day, 0:00:00' or '0:05:00':
        # return str(obj)

    elif isinstance(obj, Decimal):
        return float(obj) # Or str(obj) for exact precision

    elif isinstance(obj, dict):
        return {k: convert_unserializable_types_for_json(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [convert_unserializable_types_for_json(elem) for elem in obj]

    return obj