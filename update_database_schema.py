import argparse
import sqlite3 as lite
import logging
logger = logging.getLogger(__name__)

import tqdm

from utils import tqdmForLogging, flatten

def main(database_filename, schema_filename):
    with lite.connect(database_filename) as connection:
        cur = connection.cursor()
        
        tables = cur.execute("select name from sqlite_master where type='table'").fetchall()
        tables = flatten(tables)
        tables.remove('sqlite_sequence')
        logger.debug('Got tables=%s', tables)
        
        renamed_tables = list(map(lambda name: name + '2', tables))
        
        for table, renamed_table in zip(tables, renamed_tables):
            logger.debug('Renaming table %s to %s', table, renamed_table)
            cur.execute(f'alter table {table} rename to {renamed_table}')
            
        with open(schema_filename, 'r') as f:
            schema = f.read()
        
        logger.debug('Executing schema file %s', schema_filename)
        cur.executescript(schema) # surely this is safe ;)
        
        for table, renamed_table in zip(tables, renamed_tables):
            logger.debug('Copying data from %s to new table %s', renamed_table, table)
            
            # Get all column names from the old table
            cur.execute(f'select * from {renamed_table}')
            old_column_names = list(map(lambda t: t[0], cur.description))
            
            # Get all column names from the new table
            cur.execute(f'select * from {table}')
            new_column_names = list(map(lambda t: t[0], cur.description))
            
            column_names = set(old_column_names) & set(new_column_names)
            columns_str = ','.join(column_names)
            logger.debug('Copying only shared columns %s', columns_str)
            
            # Copy data to new table
            cur.execute(f'insert into {table} ({columns_str}) select {columns_str} from {renamed_table}')
        
        for renamed_table in renamed_tables:
            logger.debug('Dropping old table %s', renamed_table)
            cur.execute(f'drop table {renamed_table}')
    
    with lite.connect(database_filename) as connection:
        logger.debug('Vacuuming')
        connection.execute('vacuum')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stupid thing that expands/reorders the schema')
    parser.add_argument('database', type=str)
    parser.add_argument('schema', type=str)
    
    #subparsers?
    parser.add_argument('--logging-level', type=int, default=logging.WARNING,
                        help="Set the logging level")

    args = parser.parse_args()
    
    logging.basicConfig(stream=tqdmForLogging, level=args.logging_level)

    main(args.database, args.schema)