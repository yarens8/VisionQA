
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from database import get_db
from executors.database.db_executor import DatabaseExecutor

router = APIRouter(prefix="/db-test", tags=["db-test"])

class DBQuerySchema(BaseModel):
    connection_string: str
    query: str
    params: Optional[Dict[str, Any]] = None

class DBSchemaValidationSchema(BaseModel):
    connection_string: str
    table_name: str
    expected_columns: List[str]

@router.post("/query")
def run_db_query(data: DBQuerySchema):
    """Veritabanında sorgu çalıştırır."""
    executor = DatabaseExecutor(data.connection_string)
    return executor.execute_query(data.query, data.params)

@router.post("/validate-schema")
def validate_db_schema(data: DBSchemaValidationSchema):
    """Tablo şemasını doğrular."""
    executor = DatabaseExecutor(data.connection_string)
    return executor.validate_schema(data.table_name, data.expected_columns)

@router.get("/tables")
def get_db_tables(connection_string: str):
    """Veritabanındaki tabloları listeler."""
    from sqlalchemy import inspect
    from sqlalchemy import create_engine
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    return inspector.get_table_names()

