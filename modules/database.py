# Copyright 2020 Артём Воронов
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import sqlite3
import os
from modules.baselogger import get_logger
log = get_logger("db")


class DataBase:
    def __init__(self, path):
        """
        May create and connect to unique SQLite3 database
        :param path: Path to the db file
        """
        try:
            self.__path = path

            if not os.path.exists("data/databases"):
                if not os.path.exists("data"):
                    os.mkdir("data")
                os.mkdir("data/databases")
                log.info(f"Created dir: data/databases/")

            self.__conn = sqlite3.connect(self.__path)
            self.__cursor = self.__conn.cursor()
        except sqlite3.Error as e:
            log.error(e)

    def create_table(self, name, *args, id_replace=None, check_mode=False):
        """
        Create a new table
        :param name: Name of new table
        :param args: strings of columns for table. Def: id PRIMARY KEY UNIQUE NOT NULL
        :param id_replace: replace id column
        :param check_mode: If true, create new table only if it doesn't exist
        :return: bool
        """
        try:
            columns = ""
            for arg in args:
                columns = columns + ", " + arg

            if check_mode:
                name = "if not exists " + name  # if check_mode = True, we get "CREATE TABLE if not exists" execute

            if id_replace:
                self.__cursor.execute(f"""CREATE TABLE {name} ({id_replace}{columns});""")
            else:
                self.__cursor.execute(f"""CREATE TABLE {name} (id PRIMARY KEY UNIQUE NOT NULL{columns});""")
            self.__conn.commit()

            log.info(f"[{self.__path}] Create new table {name} with (id PRIMARY KEY UNIQUE NOT NULL{columns})")
            return True
        except sqlite3.Error as e:
            handler_errors = ["table Guilds already exists", "table Members already exists", "table Orgs already exists", "table Shop already exists"]
            if str(e) in handler_errors:
                if str(e) == "table Guilds already exists":
                    log.info("Table Guilds already exists, reading guilds data.")
                return False
            log.error(e)
            return False

    def insert(self, table, columns="", values=""):
        """
        Represent an INSERT SQlite3 execute
        :param table: Table name
        :param columns: Columns you want to insert
        :param values: Values of inserting columns
        :return: bool
        """
        try:
            if columns:
                columns = f"({columns})"
            self.__cursor.execute(
                f"""INSERT INTO {table}{columns} VALUES({values});""")
            self.__conn.commit()
            log.info(f"[{self.__path}] Insert row in {table}{columns} VALUES({values})")
            return True
        except sqlite3.Error as e:
            log.error(e)
            return False

    def update(self, table, key_column, key, column, value):
        """
        Represent an UPDATE SQlite3 execute
        :param table: Table name
        :param key_column: Column by which you want to search for an updating row
        :param key: Value of key column in the updating row
        :param column: Column you want to update
        :param value: New value for updating column
        :return: bool
        """
        try:
            self.__cursor.execute(
                f"""UPDATE {table} SET {column} = {value} where {key_column} = {key};""")
            self.__conn.commit()
            return True
        except sqlite3.Error as e:
            log.error(e)
            return False

    def delete(self, table, key_column, key):
        """
        Represent an DELETE SQlite3 execute
        :param table: Table name
        :param key_column: Column by which you want to search for an deleting row
        :param key: Value of key column in the deleting row
        :return: bool
        """
        try:
            self.__cursor.execute(f"""DELETE FROM {table} where {key_column} = {key};""")
            self.__conn.commit()
            return True
        except sqlite3.Error as e:
            log.error(e)
            return False

    def read(self, table, key_column, key, columns_to_read="*"):
        """
        Represent an SELECT.fetchone SQlite3 execute
        :param table: Table name
        :param key_column: Column by which you want to search for an deleting row
        :param key: Value of key column in the deleting row
        :param columns_to_read: Default set to all
        :return: result
        """
        try:
            result = self.__cursor.execute(f"""SELECT {columns_to_read} FROM {table} where {key_column} = {key};""").fetchone()
            return result
        except sqlite3.Error as e:
            log.error(e)
            return None

    def read_many(self, table, size, columns_to_read="*"):
        """
        Represent an SELECT.fetchmany SQlite3 execute
        :param table: Table name
        :param size: Number of selected rows
        :param columns_to_read: Default set to all
        :return: result
        """
        try:
            result = self.__cursor.execute(f"""SELECT {columns_to_read} FROM {table};""").fetchmany(size)
            return result
        except sqlite3.Error as e:
            log.error(e)
            return None

    def read_all(self, table, columns_to_read="*"):
        """
        Represent an SELECT.fetchall SQlite3 execute
        :param table: Table name
        :param columns_to_read: Default set to all
        :return: result
        """
        try:
            result = self.__cursor.execute(f"""SELECT {columns_to_read} FROM {table};""").fetchall()
            return result
        except sqlite3.Error as e:
            log.error(e)
            return None

    def read_all_by_order(self, table, order_key, columns_to_read="*", mod="ASC"):
        """
        Represent an ordered SELECT.fetchall SQlite3 execute
        :param table: Table name
        :param order_key: Column by which you want to sort
        :param columns_to_read: Default set to all
        :param mod: Sorting order: ASC (default) / DESC
        :return: result
        """
        try:
            result = self.__cursor.execute(f"SELECT {columns_to_read} FROM {table} ORDER BY {order_key} {mod};").fetchall()
            return result
        except sqlite3.Error as e:
            log.error(e)
            return None

