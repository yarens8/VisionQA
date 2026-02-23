
import time
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

class DatabaseExecutor:
    """
    🗄️ VisionQA — Database Executor
    Veritabanı şeması doğrulama, sorgu performansı ve veri bütünlüğü kontrolleri yapar.
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.history = []

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Bir SQL sorgusu çalıştırır ve performansını ölçer."""
        start_time = time.time()
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(query), params or {})
                # Select sorgusu ise verileri çek
                if result.returns_rows:
                    rows = [dict(row._mapping) for row in result.all()]
                    row_count = len(rows)
                else:
                    rows = []
                    row_count = result.rowcount

            duration = (time.time() - start_time) * 1000
            res = {
                "success": True,
                "data": rows,
                "row_count": row_count,
                "duration_ms": round(duration, 2),
                "query": query
            }
        except Exception as e:
            res = {
                "success": False,
                "error": str(e),
                "duration_ms": round((time.time() - start_time) * 1000, 2),
                "query": query
            }
        
        self.history.append(res)
        return res

    def validate_schema(self, table_name: str, expected_columns: List[str]) -> Dict[str, Any]:
        """Belirtilen tablonun sütun yapısını kontrol eder."""
        start_time = time.time()
        try:
            inspector = inspect(self.engine)
            columns = [c['name'] for c in inspector.get_columns(table_name)]
            
            missing = [col for col in expected_columns if col not in columns]
            
            res = {
                "success": len(missing) == 0,
                "table": table_name,
                "actual_columns": columns,
                "missing_columns": missing,
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            res = {
                "success": False,
                "error": str(e),
                "duration_ms": round((time.time() - start_time) * 1000, 2)
            }
        return res

    def check_table_count(self, table_name: str, min_expected: int = 0) -> Dict[str, Any]:
        """Tablodaki satır sayısını kontrol eder."""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        res = self.execute_query(query)
        if res["success"]:
            count = res["data"][0]["count"]
            res["validation_passed"] = count >= min_expected
            res["count"] = count
        return res
