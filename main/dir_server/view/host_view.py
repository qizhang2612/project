from main.dir_server.data_provider.data_provider import DataProvider
from typing import List
from typing import Tuple
from typing import Dict
from typing import Any
from typing import NoReturn


HOST_YAML_PATH = './main/dir_server/conf/host_config.yaml'


def record_pub_info(group_address, location, topic_name):
    """Deal with the publishing request

    Args:
        group_address: the multicast address representing the topic
        location: the location of the topic
        topic_name: the topic's name
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    # delete history pub info, make sure only one address recorded.
    data_provider.delete("address", op="pub")
    data_provider.insert("address", ("pub", group_address,
                                     location, topic_name))


def record_sub_info(ipv4_address, location, topic_name):
    """Deal with the subscribing request

    Args:
        ipv4_address: the IP address of the topic
        location: the location of the topic
        topic_name: the topic's name
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    data_provider.insert("address", ("sub", ipv4_address,
                                     location, topic_name))


def get_pub_address():
    """Get the topic's multicast address

    Returns:
        the topic's multicast address
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    pub_channels = data_provider.get("channels_pub")

    if pub_channels:
        pub_channel = pub_channels[0]
        channel_info = data_provider.get("channel" + "_" + pub_channel)
        return channel_info["address"]
    else:
        return None


def get_sub_info():
    """Get all subscribed topic's information

    Returns:
        A list containing the subscribed topic's information
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    sub_channels = data_provider.get("channels_sub")

    channels_info = []
    for sub_channel in sub_channels:
        channel_info = data_provider.get("channel" + "_" + sub_channel)
        channels_info.append([channel_info["address"],
                              channel_info["location"]])
    return channels_info


def get_channel_history(channel: str) -> List[str]:
    """Get history of specific channel.

    Returns:
        A list of available msg.
        Empty list will return if nothing got.

        examples:
        ['msg1', 'msg2']
        []
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    key = "history" + "_" + channel
    channels = data_provider.get(key)
    result = channels if channels else []
    return result


def get_channel_history(channel: str) -> List[str]:
    """Deal with history geting request.

    Args:
        channel: the sending topic's name

    Returns:
        All the history which the topic has sent
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    res = data_provider.get('history_'+channel)
    return res


def record_history_msg(value: Tuple) -> NoReturn:
    """Deal with history recording request.

    Args:
        value: A tuple describe this history line,
        the elements must suit with corresponding
        db table.
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    data_provider.insert("history", value)


def delete_sub_info(ipv4_address, location, topic_name):
    """Deal with subscriber's deleting request.

    Args:
        ipv4_address: subscriber's address
        location: subscriber's location
        topic_name: subscriber's topic name
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    data_provider.delete("address", op='sub',
                         address=ipv4_address,
                         location=location,
                         topic_name=topic_name)


def delete_pub_info(ipv4_address, location, topic_name):
    """Deal with the topic deleting request

    Args:
        ipv4_address: the IPv4 address of the topic
        location: the location of the topic
        topic_name: the topic's name
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    data_provider.delete('address', op='pub')


def record_recv_channel(channel: str):
    """Deal with the recording the received topic request

    Args:
        channel: the name of the topic, from which received message
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    data_provider.insert("senders", '(\'' + channel + '\')')


def get_recv_channel():
    """Deal the querying all topics' name, from which received message

    Returns:
        A list contains all the topics' name,
        from which received message
    """
    data_provider = DataProvider(config_path=HOST_YAML_PATH)
    res = data_provider.get('senders')
    return res
