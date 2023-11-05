import pymysql
import logging
from typing import Dict
from typing import Any
from typing import List
from typing import Tuple
from typing import NoReturn


class MysqlManager(object):
    """Provide interface for MySQL management.

    Writing operations are provided for applications.
    Getting operation is only provided for updating cache.

    Attributes:
        mysql_conn: A pymysql.connect Object to custom
        the connection host, db and user info.
    """
    def __init__(self, mysql_connection):
        self.mysql_conn = mysql_connection

    def __del__(self):
        self.mysql_conn.close()

    def get(self, key: str, key_config: Dict[str, Any])\
            -> List[Tuple[Any]]:
        """look up database when cache is missing.

        This function is not available for providing data directly.

        Args:
            key: A string of topic name with prefix.
            key_config: A dict loaded in config.yaml

        Returns:
            A List of tuples representing the selected results.
            each tuple represent of a single row with
            selected cols in db table.
        """
        cursor = self.mysql_conn.cursor()
        table = key_config['table']
        col = key_config['col']
        if type(col) == list:
            col = ",".join(col)
        select_key = key_config['key']
        if select_key:
            condition = key.split('_')[1]
            sql = "select " + col + " from " + table + " where " + select_key + " = '%s'" % condition
        else:
            sql = "select " + col + " from " + table
        logging.info("SQL executed-" + sql)
        cursor.execute(sql)
        result = cursor.fetchall()
        return result

    def get_from_db(self, table_name: str, conditions: Dict[str, Any], col: str) \
            -> List[Tuple[Any]]:
        """Get values from table.

        This function is only provided for applications
        that require strong consistency.

        Args:
            table_name: A string of table name.
            conditions: A dict representing select conditions.
            col: A string of col to be selected.

        Returns:
            A List of tuples representing the selected results.
            each tuple represent of a single row with
            selected cols in db table.
        """
        cursor = self.mysql_conn.cursor()
        if conditions:
            condition_exp = self._generate_condition_exp(conditions)
            sql = "SELECT " + col + " FROM " + table_name + " WHERE " + condition_exp
        else:
            sql = "SELECT " + col + " FROM " + table_name
        logging.info("SQL executed-" + sql)
        cursor.execute(sql)
        result = cursor.fetchall()
        return result

    def insert(self, table_name: str, value: Tuple[Any]) -> NoReturn:
        """Insert value into table.

        Args:
            table_name: A string of table name.
            value: A tuple representing a row in the table.
        """
        cursor = self.mysql_conn.cursor()
        sql = "INSERT INTO " + table_name + \
              " VALUES " + str(value)
        logging.info("SQL executed-" + sql)
        try:
            cursor.execute(sql)
        except Exception as e:
            print('Wrong at db operation')
        self.mysql_conn.commit()
        logging.info("Row count-" + str(cursor.rowcount))

    def delete(self, table_name: str, conditions: Dict[str, Any]) -> NoReturn:
        """Delete record in db.

        Args:
            table_name: A string of table name.
            conditions: A dict representing select conditions.
        """
        cursor = self.mysql_conn.cursor()
        condition_exp = self._generate_condition_exp(conditions)
        if conditions:
            sql = "DELETE FROM " + table_name + " WHERE " + condition_exp
        else:
            sql = "DELETE FROM " + table_name
        logging.info("SQL executed-" + sql)
        cursor.execute(sql)
        self.mysql_conn.commit()
        logging.info("Row count-" + str(cursor.rowcount))

    def update(self, table_name: str, key: str, value: Any,
               select_key: str, select_value: Any) -> NoReturn:
        """update record in db.

        Args:
            table_name: A string of table name.
            key: A string of col to be updated.
            value: A string of value corresponding the key to be set.
            select_key: A string of selected col.
            select_value: A string of value of the selected col.
        """
        cursor = self.mysql_conn.cursor()
        if type(value) == str:
            value = "'" + value + "'"
        if type(select_key) == str:
            select_value = "'" + select_value + "'"
        sql = "UPDATE " + table_name + " SET " + key + "=" + value + \
              " WHERE " + select_key + "=" + select_value
        logging.info("SQL executed-" + sql)
        cursor.execute(sql)
        self.mysql_conn.commit()
        logging.info("Row count-" + str(cursor.rowcount))

    @staticmethod
    def _generate_condition_exp(conditions: Dict[str, Any]) -> str:
        """generate the SQL condition

        When we want do some operation in db, we use the xxx when {some condition},
        we don't want to contract the condition again and again, so we write the function

        Args:
            the condition

        Returns:
            the string of the condition
        """
        condition_exp = ""
        count = 0
        for key, value in conditions.items():
            if count != 0:
                condition_exp += " AND "
            count += 1

            if type(value) == str:
                condition_exp += key + "='" + value + "'"
            else:
                condition_exp += key + "=" + value
        return condition_exp
