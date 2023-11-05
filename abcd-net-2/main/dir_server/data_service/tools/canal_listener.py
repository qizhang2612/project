import time
import redis
import yaml
import logging
import argparse
from canal.client import Client
from canal.protocol import EntryProtocol_pb2
from canal.protocol import CanalProtocol_pb2
from typing import Dict
from typing import List
from typing import NoReturn
from typing import Any

from main.dir_server.data_service.redis_manager import RedisManager


def connect_canal() -> Client:
    """Establish connection to canal server.

    Return:
        A canal.client instance.
    """
    client = Client()
    client.connect(host='127.0.0.1', port=11111)
    client.check_valid(username=b'', password=b'')
    client.subscribe(client_id=b'1001', destination=b'example', filter=b'.*\\..*')
    return client


def load_config(config_file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Generate table describe config.

    Args:
        config_file_path: the yaml file's path
    Return:
        A dict record all table-[key_record,] pairs.
    """
    with open(config_file_path, "r") as fp:
        raw_config = yaml.load(fp, Loader=yaml.FullLoader)
    config = dict()
    for key, item in raw_config.items():
        if key == 'database':
            continue
        table_name = item['table']
        if table_name not in config.keys():
            config[table_name] = []

        item['prefix'] = key
        config[table_name].append(item)

    return config


def fetch_log_data(client: Client) -> List[Dict[str, Any]]:
    """Periodically extract data from canal.

    Args:
        client:
            A canal.client instance.

    Return:
        A list of log data.
        example:
            [{'db': 'pub_sub', 'table': 'sub', 'event_type': 3,
            'data': {'topic_name': 'topic1', 'subscriber': '20.0.0.1'}}]
    """
    message = client.get(100)
    entries = message['entries']
    log_data = []
    for entry in entries:
        entry_type = entry.entryType
        if entry_type in [EntryProtocol_pb2.EntryType.TRANSACTIONBEGIN, EntryProtocol_pb2.EntryType.TRANSACTIONEND]:
            continue
        row_change = EntryProtocol_pb2.RowChange()
        row_change.MergeFromString(entry.storeValue)
        header = entry.header
        database = header.schemaName
        table = header.tableName
        event_type = header.eventType
        # '1': insert, '2': update, '3': delete
        for row in row_change.rowDatas:
            format_data = dict()
            if event_type == EntryProtocol_pb2.EventType.DELETE:
                for column in row.beforeColumns:
                    format_data[column.name] = column.value
            elif event_type == EntryProtocol_pb2.EventType.INSERT:
                for column in row.afterColumns:
                    format_data[column.name] = column.value
            else:
                format_data['before'] = dict()
                format_data['after'] = dict()
                for column in row.beforeColumns:
                    format_data['before'][column.name] = column.value
                for column in row.afterColumns:
                    format_data['after'][column.name] = column.value
            row_data = dict(
                db=database,
                table=table,
                event_type=event_type,
                data=format_data,
            )
            log_data.append(row_data)
    return log_data


def update_cache(log_data: List[Dict[str, Any]], manager: RedisManager,
                 config: Dict[str, List[Dict[str, Any]]]) -> NoReturn:
    """Update cache by parsing binlog.

    Args:
        log_data: A list of binlog data.
        manager: A RedisManager instance.
        config: A dict record all table-[key_record,] pairs.
    """
    for log_item in log_data:
        if log_item['event_type'] == EntryProtocol_pb2.EventType.INSERT:
            manager.insert_from_log(log_item, config)
        elif log_item['event_type'] == EntryProtocol_pb2.EventType.UPDATE:
            manager.update_from_log(log_item, config)
        elif log_item['event_type'] == EntryProtocol_pb2.EventType.DELETE:
            manager.delete_from_log(log_item, config)
        else:
            pass


if __name__ == "__main__":
    """Connect to canal, Periodically extract binlog data from it.
    Then update cache by binlog.
    """
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)s:%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--ishost', action='store_true')
    args = parser.parse_args()
    if args.ishost:
        config_path = './main/dir_server/conf/host_config.yaml'
    else:
        config_path = './main/dir_server/conf/server_config.yaml'

    canal_client = connect_canal()
    redis_conn = redis.Redis(host='localhost', port=6379, decode_responses=True)
    redis_manager = RedisManager(redis_conn)
    table_config = load_config(config_path)
    logging.info("load table config:\n" + str(table_config))

    while True:
        try:
            log = fetch_log_data(canal_client)
            if log:
                logging.info("receive log:" + str(log))
                update_cache(log, redis_manager, table_config)
            else:
                time.sleep(0.1)
        except KeyboardInterrupt:
            canal_client.disconnect()
            break
