"""
Read-only FastAPI service over the brewery SQLite database.

Run `python main.py` first to build the database, then:
    uvicorn src.api:app --reload
Open http://127.0.0.1:8000/docs for the API docs.
"""

import os
import sqlite3
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel

DB_PATH = os.path.join("data", "database", "breweries.db")

app = FastAPI(
    title="Open Brewery ETL API",
    description="Read-only access to the processed brewery dataset and the analysis answers.",
    version="1.0.0",
)


class Brewery(BaseModel):
    id: str
    name: Optional[str] = None
    brewery_type: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None


class StateCount(BaseModel):
    state_province: str
    microbrewery_count: int


class PhonePattern(BaseModel):
    state_province: str
    phone_type: str
    frequency: int


class IncheonResult(BaseModel):
    province: str
    country: str
    brewpub_count: int


def get_db():
    """Yields a read-only SQLite connection or fail clearly if the DB is missing."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail="Database not found. Build it first by running: python main.py",
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@app.get("/", tags=["System"])
def index():
    """Landing route: point visitors at the docs and list the available endpoints."""
    return {
        "service": "Open Brewery ETL API",
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/breweries",
            "/breweries/{id}",
            "/analytics/top-microbrewery-states",
            "/analytics/incheon-brewpubs",
            "/analytics/korea-phone-patterns",
        ],
    }


@app.get("/health", tags=["System"])
def health():
    """Liveness check plus whether the database is present."""
    return {"status": "ok", "database_present": os.path.exists(DB_PATH)}


@app.get("/breweries", response_model=list[Brewery], tags=["Breweries"])
def list_breweries(
    conn: sqlite3.Connection = Depends(get_db),
    country: Optional[str] = None,
    state_province: Optional[str] = None,
    brewery_type: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List breweries with optional filters and pagination."""
    # Build WHERE from the filters that were supplied
    clauses = []
    params: list = []
    for column, value in [
        ("country", country),
        ("state_province", state_province),
        ("brewery_type", brewery_type),
        ("city", city),
    ]:
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT id, name, brewery_type, city, state_province,
               postal_code, country, phone, website_url
        FROM breweries
        {where}
        ORDER BY name
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.get("/breweries/{brewery_id}", response_model=Brewery, tags=["Breweries"])
def get_brewery(brewery_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Fetch a single brewery by its id."""
    row = conn.execute(
        """
        SELECT id, name, brewery_type, city, state_province,
               postal_code, country, phone, website_url
        FROM breweries WHERE id = ?
        """,
        (brewery_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Brewery '{brewery_id}' not found")
    return dict(row)


@app.get("/analytics/top-microbrewery-states", response_model=list[StateCount], tags=["Analytics"])
def top_microbrewery_states(
    conn: sqlite3.Connection = Depends(get_db),
    limit: int = Query(5, ge=1, le=50),
):
    """Q1 and Q2: US states ranked by microbrewery count."""
    rows = conn.execute(
        """
        SELECT state_province, COUNT(*) AS microbrewery_count
        FROM breweries
        WHERE country = 'United States' AND brewery_type = 'micro'
        GROUP BY state_province
        ORDER BY microbrewery_count DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


@app.get("/analytics/incheon-brewpubs", response_model=IncheonResult, tags=["Analytics"])
def incheon_brewpubs(conn: sqlite3.Connection = Depends(get_db)):
    """Q3: number of brewpubs in Incheon, South Korea."""
    count = conn.execute(
        """
        SELECT COUNT(*) FROM breweries
        WHERE country = 'South Korea'
          AND brewery_type = 'brewpub'
          AND state_province = 'Incheon'
        """
    ).fetchone()[0]
    return {"province": "Incheon", "country": "South Korea", "brewpub_count": count}


@app.get("/analytics/korea-phone-patterns", response_model=list[PhonePattern], tags=["Analytics"])
def korea_phone_patterns(conn: sqlite3.Connection = Depends(get_db)):
    """Q4: South Korean phone-type distribution by province."""
    rows = conn.execute(
        """
        SELECT state_province, phone_type, COUNT(*) AS frequency
        FROM breweries
        WHERE country = 'South Korea' AND phone_prefix IS NOT NULL
        GROUP BY state_province, phone_type
        ORDER BY state_province ASC, frequency DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]
