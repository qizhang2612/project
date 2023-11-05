import json


def get_json(file_path: str):
    with open(file_path, 'r') as file:
        result = json.load(file)
    return result


def get_msg(msg: str):
    json_msg = json.loads(msg)
    if 'msg' not in json_msg:
        return {}
    else:
        return json_msg['msg']


def print_json(data: dict):
    print(json.dumps(data, sort_keys=True, indent=4, separators=(', ', ': ')))


def check_keys(json_dict: dict, keys: list):
    """Easy function for checking some keys' existing
    """
    for key in keys:
        if key not in json_dict:
            return False
    return True
