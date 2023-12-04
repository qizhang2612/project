from main.dir_server.data_provider.data_provider import DataProvider
from typing import List
from typing import Tuple
from typing import Dict
from typing import Any
from typing import NoReturn


SERVER_YAML_PATH = './main/dir_server/conf/server_config.yaml'


def get_topics(strong_consistent=False) -> List[str]:
    """Get all available topics.

    Args:
        strong_consistent: A boolean var indicate weather
        load data directly from db, False in default.

    Returns:
        A list of available topics in directory server.
        each element is a topic string.

        Empty list will return if nothing got.

        examples:
        ['topic1', 'topic2']
        []
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    if strong_consistent:
        raw_result = data_provider.get_from_db("pub", {}, "topic_name")
        result = [ele[0] for ele in raw_result]
    else:
        channels = data_provider.get("channels")
        result = channels if channels else []
    return result


def get_groups() -> List[str]:
    """Get all used topics.

    Returns:
        A list of used topics in directory server.
        each element is a group address string.

        Empty list will return if nothing got.

        example:
        ['232.0.0.1', '232.0.0.2']
        []
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    raw_result = data_provider.get_from_db("pub", {}, "group_addr")
    result = [ele[0] for ele in raw_result]
    return result


def get_topic_info(topic_name: str) \
        -> Dict[str, Any]:
    """Get info of specific topic.

    Args:
        topic_name: A string of topic name.

    Returns:
        A dict to describe topic.

        Empty dict will be returned if
        no topic info was found.

        example:
        {'type': 'type1', 'location': 'area A', ...}
        {}
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    key = "topic" + "_" + topic_name
    topic_info = data_provider.get(key)
    result = topic_info if topic_info else {}
    return result


def get_sub_list(topic_name: str) \
        -> List[str]:
    """Get subscribers of a specific topic.

    Args:
        topic_name: A string of topic name.

    Returns:
        A List contains all subscriber of this topic.
        Empty list will return if nothing got.

        example:
        ['h1', 'h2']
        []
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    key = "sub" + "_" + topic_name
    sub_list = data_provider.get(key)
    result = sub_list if sub_list else []
    return result


def publish_new_topic(value: Tuple) -> NoReturn:
    """Deal with topic publish request.

    Args:
        value: A tuple describe this new topic,
        the elements must suit with corresponding
        db table.
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    data_provider.insert("pub", value)


def delete_topic(topic_name: str) -> NoReturn:
    """Deal with topic delete request.

    Args:
        topic_name: A string of topic name to be deleted.
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    data_provider.delete("pub", topic_name=topic_name)


def subscribe_topic(topic_name: str, subscriber: str) -> NoReturn:
    """Deal with topic subscribe request.

    Args:
        topic_name: A string of subscribe topic.
        subscriber: A string of subscriber ip.
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    value = (topic_name, subscriber)
    data_provider.insert("sub", value)


def unsubscribe_topic(topic_name: str, subscriber: str) -> NoReturn:
    """Deal with topic unsubscribe request.

    Args:
        topic_name: A string of unsubscribe topic.
        subscriber: A string of subscriber ip.
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    data_provider.delete("sub", topic_name=topic_name, subscriber=subscriber)


def register_host(value: Tuple) -> NoReturn:
    """Register subscriber info.

    Args:
        value: A tuple describe this host,
        the elements must suit with corresponding
        db table.
    """

    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    data_provider.insert("host", value)


def get_hosts():
    """Get all registered hosts.

    Returns:
        A list of all registered hosts in directory server.
        each element is a host name string.

        Empty list will return if nothing got.

        examples:
        ['host1', 'host2']
        []
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    hosts = data_provider.get("hosts")
    result = hosts if hosts else []
    return result


def get_host_info(host_name: str) \
        -> Dict[str, Any]:
    """Get info of specific host.

    Args:
        host_name: A string of host name.

    Returns:
        A dict to describe requested host.

        Empty dict will be returned if
        no host info was found.

        example:
        {'host_name': 'h1', 'location': 'area A', ...}
        {}
    """
    data_provider = DataProvider(config_path=SERVER_YAML_PATH)
    key = "host" + "_" + host_name
    host_info = data_provider.get(key)
    result = host_info if host_info else {}
    return result


def find_host_name_by_ip(ip: str) -> str:
    """Get host name by ip address.

    Args:
        A string of host ip.

    Returns:
        A string of host name.
    """
    hosts = get_hosts()
    for host in hosts:
        host_info = get_host_info(host)
        if host_info["ip"] == ip:
            return host

    return ""


def find_ip_by_host_name(host_name: str) -> str:
    """Get ip by host_name address.

    Args:
        A string of host name.

    Returns:
        A string of ip.
    """
    host_info = get_host_info(host_name)
    if 'ip' in host_info:
        return host_info['ip']
    else:
        return ""


def find_group_by_topic_name(topic_name: str) -> str:
    """Find group address by topic_name

    """
    pass