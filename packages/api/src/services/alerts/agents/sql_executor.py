# agents/sql_executor.py
from langchain.tools import tool
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from ....core.config import settings

# Create a synchronous engine and session for SQL execution
# Convert async URL to sync URL for synchronous operations
sync_database_url = settings.DATABASE_URL.replace(
    'postgresql+asyncpg://', 'postgresql+psycopg2://'
)
sync_engine = create_engine(sync_database_url, echo=False)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


@tool
def execute_sql(sql: str) -> str:
    """Executes a SQL query and returns results or error message."""
    if not sql or sql.strip() == '':
        return 'SQL Error: Empty query'

    with SyncSessionLocal() as session:
        try:
            print(f'Executing SQL: {sql}')
            result = session.execute(text(sql))

            # Check if query returns rows
            if result.returns_rows:
                rows = result.fetchall()
                if rows:
                    # Convert each row to a tuple and then to string
                    formatted_rows = [tuple(row) for row in rows]
                    print(f'****** Formatted rows: {str(formatted_rows)}')
                    str_formatted_rows = str(formatted_rows)
                    if 'NO_ALERT' in str_formatted_rows:
                        return '[]'
                    if 'NOT_APPLICABLE' in str_formatted_rows:
                        return 'SQL Error: Alert rule is invalid'
                    return str(formatted_rows)
                else:
                    print('No rows returned')
                    return '[]'
            else:
                # For non-SELECT queries (INSERT, UPDATE, DELETE)
                session.commit()
                return 'SQL executed successfully'

        except Exception as e:
            session.rollback()
            print(f'SQL Error: {e}')
            return f'SQL Error: {e}'
