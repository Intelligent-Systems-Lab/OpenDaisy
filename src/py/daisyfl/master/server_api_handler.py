# Copyright 2024 Intelligence Systems Lab. All Rights Reserved.
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
# ==============================================================================

from flask import Flask, request, make_response, Response
from typing import Callable
from daisyfl.common.task_manager import TaskManager
from daisyfl.utils.logger import log
from daisyfl.utils.logger import WARNING, ERROR, INFO, DEBUG
from daisyfl.common import TID

class ServerListener:
    """
    HTTP server to be required by users and external applications.
    This HTTP server is used to meet the following requirements:
    1. Users can publish task configurations.
    2. Users or external apps (e.g., Prometheus) can get metrics of the specific task.
    """

    def __init__(
            self,
            ip: str,
            port: int,
            task_manager: TaskManager,
        ):
        self.app = Flask(__name__)
        self._ip: str = ip
        self._port: int = port
        self._task_manager: TaskManager = task_manager
        self.get_metrics = None
        
        @self.app.route("/publish_task", methods=["POST"])
        def publish_task():
            """Publish a task configuration with JSON format to the Master node."""
            js = request.get_json()
            _, report =self._task_manager.receive_task(task_config=js)
            self.get_metrics(report.config[TID])
            return js, 200
        
        @self.app.route("/metrics")
        def metrics():
            """
            Expose Daisy metrics to Prometheus or other tools.
            """
            task_id = request.args.get('task_id', None)
            if task_id is None:
                log(WARNING, "Requested task id doesn't exist.")
                response = make_response("")
                response.headers["content-type"] = "text/plain"
                return response
            if self.get_metrics is None:
                log(WARNING, "get_metrics isn't defined.")
                response = make_response("")
                response.headers["content-type"] = "text/plain"
                return response
            return self.get_metrics(task_id)

    def run(self,):
        """Run this HTTP server."""
        self.app.run(host=self._ip, port=self._port)
    
    def set_get_metrics(self, get_metrics_fn: Callable) -> None:
        """Set a callback function to get metrics of a specific task."""
        self.get_metrics = get_metrics_fn

