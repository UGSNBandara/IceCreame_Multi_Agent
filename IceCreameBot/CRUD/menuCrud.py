from typing import List
from CRUD.db import get_db
from Cache.MenuCache import MenuItemDTO

async def fetch_menu_items() -> List[MenuItemDTO]:
    db = await get_db()
    docs = await db["menu"].find({}, {"_id": 0}).to_list(length=2000)
    out: List[MenuItemDTO] = []
    for r in docs:
        try:
            out.append(
                MenuItemDTO(
                    id=int(r["id"]),
                    name=str(r["name"]),
                    description=str(r.get("description", "")),
                    price=float(r.get("price", 0.0)),
                )
            )
        except Exception:
            continue
    return out
