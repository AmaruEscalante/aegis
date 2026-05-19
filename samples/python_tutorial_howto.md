# How to Build a REST API with FastAPI and PostgreSQL

This guide walks through building a production-ready REST API from scratch using FastAPI, SQLAlchemy, and PostgreSQL.

## Prerequisites

- Python 3.11+
- Docker (for PostgreSQL)
- `pip` or `uv` for package management

## Step 1: Set Up the Project

```bash
mkdir myapi && cd myapi
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic
```

## Step 2: Start PostgreSQL with Docker

```bash
docker run --rm -d \
  --name pg-dev \
  -e POSTGRES_USER=dev \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=myapi \
  -p 5432:5432 \
  postgres:16
```

## Step 3: Define Your Models

Create `models.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

## Step 4: Create the FastAPI App

Create `main.py`:

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas
from .database import get_db

app = FastAPI(title="My API", version="1.0.0")

@app.get("/items/{item_id}", response_model=schemas.Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

## Step 5: Run the Server

```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive Swagger UI.

## Common Pitfalls

**N+1 queries**: Use `joinedload` or `selectinload` from SQLAlchemy when fetching related objects in a list endpoint.

**Missing indexes**: Always index foreign key columns and any columns used in WHERE clauses.

**No pagination**: Add `skip` and `limit` query parameters to list endpoints from day one — retrofitting pagination is painful.
