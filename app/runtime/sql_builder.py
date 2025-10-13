from typing import Dict, Any, List

class SQLBuilder:
    def __init__(self, table: str, columns: List[str]):
        self.table = table
        self.columns = columns
    def select(self, where: str, order: List[Dict[str,str]], limit: int, offset: int) -> str:
        cols = ", ".join(self.columns)
        sql = f"SELECT {cols} FROM {self.table}"
        if where:
            sql += f" WHERE {where}"
        if order:
            order_clause = ", ".join([f"{o['field']} {o.get('dir','ASC')}" for o in order])
            sql += f" ORDER BY {order_clause}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        if offset:
            sql += f" OFFSET {int(offset)}"
        return sql
