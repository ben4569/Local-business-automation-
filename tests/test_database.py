import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database
pytestmark=pytest.mark.integration
def _configured()->bool:
    return all(os.getenv(name) for name in ("MYSQL_HOST","MYSQL_PORT","MYSQL_USER","MYSQL_PASSWORD","MYSQL_DATABASE"))
@pytest.mark.skipif(not _configured(),reason="MySQL environment variables are not configured")
def test_database_connection():
    assert database.get_connection_test() is True
@pytest.mark.skipif(not _configured(),reason="MySQL environment variables are not configured")
def test_database_exists():
    row=database.fetch_one("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME=%s",(os.environ["MYSQL_DATABASE"],))
    assert row is not None
@pytest.mark.skipif(not _configured(),reason="MySQL environment variables are not configured")
@pytest.mark.parametrize("table",["users","businesses","products"])
def test_required_table_exists(table):
    row=database.fetch_one("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s",(os.environ["MYSQL_DATABASE"],table))
    assert row is not None
