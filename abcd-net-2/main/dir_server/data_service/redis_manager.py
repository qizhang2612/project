import redis
import logging
from typing import Any
from typing import List
from typing import Dict
from typing import NoReturn
import logging


class RedisManager(object):
    """Provide interface for Redis management.

    Provide cached date, Update cached data by loading from db and
    parsing binlog from db.

    Attributes:
        connection: A redis.Redis Object to describe the connection host and port.
    """

    def __init__(self, redis_connection):
        self.connection = redis_connection

    def __del__(self):
        del self.connection

    def get(self, key: str, key_type: str) -> Any:
        """Fetch data from cache.

        Args:
            key: A string of key name with prefix.
            key_type: 'list' or 'hash'.
        """
        if key_type == 'list':
            return self.connection.lrange(key, 0, -1)
        elif key_type == 'hash':
            return self.connection.hgetall(key)
        else:
            return None

    def set(self, key: str, result: List[str], key_config: Dict[str, Any]) -> NoReturn:
        """Update cached data by loading from db.

        Args:
            key: A string of key with prefix.
            result: A list of tuple contains the result loaded from db.
            key_config: A dict corresponding to self.config['prefix']
         """
        if not result:
            return

        key_type = key_config['type']
        if key_type == 'list':
            for ele in result:
                self.connection.lpush(key, ele[0])
        elif key_type == 'hash':
            col_list = key_config['col']
            for ele in result:
                for index, col in enumerate(col_list):
                    self.connection.hset(key, col, ele[index])
        else:
            pass

    def insert_from_log(self, log_info: Dict[str, Any],
                        table_config: Dict[str, List[Dict[str, Any]]]) -> NoReturn:
        """Insert binlog data into cache.

        Args:
            table_config: A dict record all table-[key_record,] pairs.
            log_info: A dict of binlog retrieved from canal.
                log_info format:
                {'db': 'pub_sub', 'table': 'pub', 'event_type': 1, 'data': {'topic_name': 'topic2',
                publisher': '20.0.0.1'}}
        """
        table_name = log_info['table']
        keys = self._get_relevant_keys(table_name, table_config, log_info)

        for key_record in keys:
            if key_record['type'] == 'list':
                items = self.get(key_record['key'], 'list')
                col = key_record['col']
                value = log_info['data'][col]
                if items and value not in items:
                    # deal with reading after writing but before binlog arrive situation.
                    self.connection.lpush(key_record['key'], value)
                    logging.info("insert record into " + str(key_record['key']) + " value: " + str(value))
            else:
                pass

    def delete_from_log(self, log_info: Dict[str, Any],
                        table_config: Dict[str, List[Dict[str, Any]]]) -> NoReturn:
        """Delete data in cache according to binlog.

        Args:
            table_config: A dict record all table-[key_record,] pairs.
            log_info: A dict of binlog retrieved from canal.

        Return:
        """
        table_name = log_info['table']
        keys = self._get_relevant_keys(table_name, table_config, log_info)

        for key_record in keys:
            if key_record['type'] == 'list':
                col = key_record['col']
                value = log_info['data'][col]
                self.connection.lrem(key_record['key'], 0, value)
                logging.info("delete record from " + str(key_record['key']) + " value: " + str(value))
            elif key_record['type'] == 'hash':
                self.connection.delete(key_record['key'])
                logging.info("delete record " + str(key_record['key']))
            else:
                pass

    def update_from_log(self, log_info: Dict[str, Any],
                        table_config: Dict[str, List[Dict[str, Any]]]) -> NoReturn:
        """Update data in cache according to binlog.

        Args:
            table_config: A dict record all table-[key_record,] pairs.
            log_info: A dict of binlog retrieved from canal.

        Return:
        """
        table_name = log_info['table']
        data_before = log_info['data']['before']
        data_after = log_info['data']['after']
        keys = self._get_relevant_keys(table_name, table_config, log_info)

        for key_record in keys:
            if key_record['type'] == 'list':
                col = key_record['col']
                value_before = data_before[col]
                value_after = data_after[col]
                self.connection.lrem(key_record['key'], 0, value_before)
                self.connection.lpush(key_record['key'], value_after)
                logging.info("update " + str(key_record['key']) + " value: " + str(value_after))
            elif key_record['type'] == 'hash':
                if self.get(key_record['key'], 'hash'):
                    self.connection.delete(key_record['key'])
                    cols = key_record['col']
                    for col in cols:
                        value = data_after[col]
                        self.connection.hset(key_record['key'], col, value)
                    logging.info("update " + str(key_record['key']) + " value: " + str(data_after))
            else:
                pass

    def _get_relevant_keys(self, table_name: str, table_config: Dict[str, List[Dict[str, Any]]],
                           log_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract keys related to the table.

        Args:
            table_name: A string of table name.
            table_config: A dict record all table-[key_record,] pairs.
            log_info: A dict of binlog retrieved from canal.

        Return:
            A list record keys related to the table.
            example:
                [{'type': 'hash', 'table': 'pub', 'key': 'topic_topic1', 'col': ['publisher'], 'prefix': 'topic'}]
        """
        relevant_keys = []

        keys = table_config[table_name]
        for raw_key in keys:
            prefix = raw_key['prefix']
            if raw_key['key']:
                if isinstance(raw_key['key'], list):
                    key = prefix + '_' + '$'.join([log_info['data'][item] for item in raw_key['key']])
                else:
                    if 'before' not in log_info['data'].keys():
                        suffix = log_info['data'][raw_key['key']]
                    else:
                        suffix = log_info['data']['before'][raw_key['key']]
                    key = prefix + '_' + suffix
            else:
                key = prefix

            if raw_key['type'] == 'list':
                if self.get(key, 'list'):
                    new_key = raw_key.copy()
                    new_key['key'] = key
                    relevant_keys.append(new_key)
            elif raw_key['type'] == 'hash':
                new_key = raw_key.copy()
                new_key['key'] = key
                relevant_keys.append(new_key)
            else:
                pass

        logging.debug(table_name + "-relevant keys:\n" + str(relevant_keys))
        return relevant_keys
