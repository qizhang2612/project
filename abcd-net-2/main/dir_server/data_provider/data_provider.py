import logging

import yaml
import redis
import pymysql
from main.dir_server.data_service.redis_manager import RedisManager
from main.dir_server.data_service.mysql_manager import MysqlManager
from functools import cmp_to_key
from typing import NoReturn
from typing import Any
from typing import Tuple
from typing import List
from typing import Dict


class DataProvider(object):
    """Provide a unit interface for data operations.

    While writing operations are dealt with mysql manager,
    reading operations are provided by the redis manager,
    the cache changed according to the mysql binlog in real time.

    Attributes:
        config: A dict loaded from config.yaml.
        redis_conn: A redis.Redis Object to custom
                    the connection host, port info.
        mysql_conn: A pymysql.connect Object to custom
                    the connection host, db and user info.
        redis_manager: A RedisManager instance
                    Providing interface for Redis management
        mysql_manager: A MysqlManager instance
                    Providing interface for MySQL management.
    """

    def __init__(self, config_path: str = ''):
        """Initializing function.

        Args:
            config_path: The yaml file's path
        Get .yaml file to make the redis-db read easy
        and get the connection to redis and db.
        """
        self.config_path = config_path
        self.config = self.load_config(self.config_path)
        self.redis_conn = redis.Redis(host='localhost', port=6379, decode_responses=True)
        self.mysql_conn = pymysql.connect(
            host='localhost',
            user='test', password='1',
            database='pub_sub',
            charset='utf8')
        self.redis_manager = RedisManager(self.redis_conn)
        self.mysql_manager = MysqlManager(self.mysql_conn)

    def __del__(self):
        del self.redis_manager
        del self.mysql_manager

    @staticmethod
    def load_config(config_path: str = '') -> NoReturn:
        """Load redis key config from config.yaml.

        Returns:
            A dict record custom key config.
        """
        with open(config_path, "r") as fp:
            config = yaml.load(fp, Loader=yaml.FullLoader)
        return config

    def get(self, key: str) -> Any:
        """Reading interface.

        Get data from redis. When missing, load data from db
        then update the cache.

        Args:
            key: A string of key name with prefix.
        """
        prefix = self._parse_prefix(key)
        key_type = self.config[prefix]['type']
        value = self.redis_manager.get(key, key_type)

        if value:
            logging.info("key request '" + key + "' hit in cache.")
            return value
        else:
            key_config = self.config[prefix]
            result = self._load_from_database(key, key_config)
            self._update_cache(key, result, key_config)
            return self.redis_manager.get(key, key_type)

    def get_from_db(self, table_name: str, conditions: Dict[str, Any], col: str) \
            -> List[Tuple[Any]]:
        """Get values from db.

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
        return self.mysql_manager.get_from_db(table_name, conditions, col)

    def insert(self, table_name: str, value: Tuple[Any]) -> NoReturn:
        """Insert value into db.

        Args:
            table_name: A string of table name.
            value: A tuple representing a row in the table.
        """
        self.mysql_manager.insert(table_name, value)

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
        self.mysql_manager.update(table_name, key, value, select_key, select_value)

    def delete(self, table_name: str, **conditions) -> NoReturn:
        """Delete record in db.

        Args:
            table_name: A string of table name.
            conditions: A dict representing select conditions.
        """
        self.mysql_manager.delete(table_name, conditions)

    def _parse_prefix(self, key: str) -> str:
        """Look up prefix in config which matching the key.

        Args:
            key: A string of key with prefix.
        Returns:
            Key: A string of key's prefix.
        """
        prefix = None

        matched_prefix = []
        for k in self.config.keys():
            if key.startswith(k):
                matched_prefix.append(k)

        sorted_matched_prefix = sorted(matched_prefix, key=cmp_to_key(self.custom_sorted))
        if sorted_matched_prefix:
            prefix = sorted_matched_prefix[0]

        return prefix

    @staticmethod
    def custom_sorted(x, y):
        """compare function for sort

        For example, 'channels' will match with 'channels' and 'channel',
        but what we really want the channels to match with is 'channels'.

        Args:
            the two keys who want to be compared.

        Returns:
            a boolean value representing the result.
        """
        if len(x) > len(y):
            return -1
        if len(x) < len(y):
            return 1
        return 0

    def _load_from_database(self, key: str, key_config: Dict[str, Any]) \
            -> List[Tuple[Any]]:
        """look up database when cache is missing.

        Args:
            key: A string of topic name with prefix.
            key_config: A dict corresponding to self.config['prefix']

        Returns:
            A List of tuples representing the selected results.
            each tuple represent of a single row with
            selected cols in db table.
        """
        return self.mysql_manager.get(key, key_config)

    def _update_cache(self, key: str, result: List[Tuple[str]], key_config: Dict[str, Any]) \
            -> NoReturn:
        """update record in redis.

        Args:
            key: A string of key with prefix.
            result: A list of tuple contains the result loaded from db.
            key_config: A dict corresponding to self.config['prefix']
        """
        if result:
            self.redis_manager.set(key, result, key_config)
        else:
            return
