from psycopg2 import sql
from psycopg2.extras import execute_values
import psycopg2


class Loader:
    '''
    To write structured data into the database
    '''

    def __init__(self, host, user, password, port, dbname = "postgres"):
        '''
        Establish a connection and a cursor to the database

        Parameter
        host (str) : host
        user (str) : user
        password (str) : password
        port (int) : port number
        dbname (str) : databse_name, default "postgres"

        Returns
        None
        '''
        self.database = dbname
        self.conn = psycopg2.connect(
            host = host,
            user = user,
            password = password,
            port = port,
            dbname = self.database
        )
        self.conn.autocommit = True
        self.cur = self.conn.cursor()


    def close(self):
        '''
        Terminate connections to the database

        Returns
        None
        '''
        self.conn.close()
        self.cur.close()
    
    
    def create_database(self, database_name):
        '''
        Create a new database with name

        Parameter
        database_name (str) : name of the database

        Returns
        None
        '''
        try:
             self.cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
        
        except psycopg2.errors.DuplicateDatabase as e:
            print(f"{e}")
              

    def create_table(self, table_name, format):
        '''
        Create a table in database using the format

        Parameter
        table_name (str) : name of the new table
        format (dict) : names of the columns mapped to their datatypes as strings

        Returns
        None
        '''
        try:
            columns = [sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(col_type)) for col, col_type in format.items()]
            create_table = sql.SQL("CREATE TABLE {} ({})").format(sql.Identifier(table_name),sql.SQL(", ").join(columns))

            self.cur.execute(create_table)

        except psycopg2.errors.DuplicateTable as e:
            print(f"Attempted to create table '{table_name}' but it already exists in database '{self.database}'")


    def update_table(self, table_name, data, primary_key = None):
        '''
        Write new data into the events table

        Parameters
        table_name (str) : name of the table to write to
        data (list of dicts) : data to be written into the database
        primary_key (str) : name of the column that is the primary_key of the table

        Returns
        None
        '''
        keys = data[0].keys()
        col = [sql.Identifier(k) for k in keys]
        values = [[row[k] for k in keys] for row in data]

        insert = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(col)
        )
        
        if primary_key:
            update = [
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(k), sql.Identifier(k)) for k in keys if k != primary_key
            ]
            query = insert + sql.SQL(" ON CONFLICT ({}) DO UPDATE SET ").format(sql.Identifier(primary_key)) + sql.SQL(', ').join(update)
        
        else:
            query = insert

        execute_values(self.cur, query, values)


    def read_table(self, table_name, filter:dict = None, sort:dict = None) -> list:
        '''
        Read and return data from table

        Parameters
        table_name (str) : name of the table
        '''
        try:
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
            values = []

            if filter:
                filters = []
                for col, val in filter.items():
                    filters.append(sql.SQL("{} = %s").format(sql.Identifier(col)))
                    values.append(val)
                
                query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(filters)

            if sort:
                sort_clauses = []
                for col, reverse in sort.items():
                    direction = sql.SQL("DESC") if reverse else sql.SQL("ASC")
                    sort_clauses.append(sql.SQL("{} {}").format(sql.Identifier(col), direction))
                
                query += sql.SQL(" ORDER BY ") + sql.SQL(", ").join(sort_clauses)

            self.cur.execute(query, values)
            return self.cur.fetchall()
            
        except psycopg2.Error as e:
            print(f"Error reading table {table_name}: {e}")
            return []
