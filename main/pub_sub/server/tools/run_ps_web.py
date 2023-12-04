from flask import Flask
from flask import request
import json
import aiohttp

from main.pub_sub.server.manager.pub_sub_manager import PubSubManager


app = Flask(__name__)


@app.route('/pub_sub', methods=["POST"])
async def index():
    data = request.get_json()
    manager = PubSubManager()
    result = manager.check_cmd(data)
    if not result:
        return json.dumps(manager.results)
    else:
        if manager.msg2tm:
            async with aiohttp.ClientSession('http://127.0.0.1:8080/') as session:
                async with session.post('/traffic_engining', json=manager.msg2tm) as resp:
                    result = await resp.text()
                    result = json.loads(result)
                    if result['result']:
                        await manager.pub_sub_handler(data)
                        return json.dumps(manager.results)
                    else:
                        return json.dumps(result)
        else:
            await manager.pub_sub_handler(data)
            return json.dumps(manager.results)


if __name__ == "__main__":
    app.run(host='10.0.0.100', port=8181, debug=True)
