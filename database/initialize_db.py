import os
import mysql.connector
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

def initialize_db():
    log_file = open('db_init_log.txt', 'w')
    def log(msg):
        print(msg)
        log_file.write(str(msg) + '\n')
        
    try:
        # Connect to MySQL first (without specifying a database)
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor()
        
        db_name = os.getenv('DB_NAME', 'blood_bank_v1')
        
        log(f"Dropping database {db_name} if it exists for a clean start...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
        
        log(f"Creating database {db_name}...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        
        log(f"Using database {db_name}...")
        cursor.execute(f"USE {db_name}")
        
        # Read and execute schema.sql
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        if not os.path.exists(schema_path):
            log(f"Schema file not found at {schema_path}")
            return
            
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        log("Executing schema.sql statements...")
        statements = schema_sql.split(';')
        for statement in statements:
            stmt = statement.strip()
            if stmt:
                # Basic cleaning of USE/CREATE DATABASE statements in schema.sql
                # since we already handled that part and want to ensure it uses db_name
                if stmt.upper().startswith("USE ") or stmt.upper().startswith("CREATE DATABASE "):
                    continue
                try:
                    cursor.execute(stmt)
                except mysql.connector.Error as err:
                    log(f"Error executing statement: {err}")
                    log(f"Statement prefix: {stmt[:100]}...")
        
        conn.commit()
        
        # Verify tables
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        log(f"Created tables in {db_name}: {tables}")
        
        if tables:
            log("Database initialization successful!")
        else:
            log("WARNING: No tables were created!")
        
        cursor.close()
        conn.close()
    except mysql.connector.Error as err:
        log(f"MySQL Error: {err}")
    except Exception as e:
        log(f"Error: {e}")
    finally:
        log_file.close()

if __name__ == "__main__":
    initialize_db()
