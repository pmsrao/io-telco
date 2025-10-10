import strawberry

@strawberry.type
class Ping:
    ok: bool

@strawberry.type
class Query:
    @strawberry.field
    def ping(self) -> Ping:
        return Ping(ok=True)

schema = strawberry.Schema(query=Query)

def get_schema():
    return schema
