from fastapi import FastAPI
from strawberry.asgi import GraphQL
import strawberry
from py2neo import Graph

app = FastAPI()

# Placeholder schema
@strawberry.type
class Artist:
    name: str

@strawberry.type
class Query:
    @strawberry.field
    def artist(self, id: int) -> Artist:
        return Artist(name="Miles Davis")

schema = strawberry.Schema(query=Query)
app.add_route("/graphql", GraphQL(schema))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)