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

from daisyfl.utils.logger import DEBUG, INFO, ERROR, WARNING
from typing import Dict, List, Optional, Tuple, Union, Callable

from daisyfl.common import (
    NUM_ROUNDS,
    ZONE_COMM_FREQUENCY,
    CURRENT_ROUND,
    CURRENT_ROUND_MASTER,
    CURRENT_ROUND_ZONE,
    EVALUATE,
    Parameters,
    Task,
    Report,
    MODEL_PATH,
    TID,
    EVALUATE_INTERVAL,
    EVALUATE_INIT_MODEL_MASTER,
    OPERATORS,
    MASTER_SERVER_OPERATOR,
    CLIENT_OPERATOR,
    ZONE_SERVER_OPERATOR,
    STRATEGIES,
    MASTER_STRATEGY,
    ZONE_STRATEGY,
    MIN_WAITING_TIME,
    MIN_WAITING_TIME_MASTER,
    MIN_WAITING_TIME_ZONE,
    SAVE_MODEL,
    MASTER_METRICS_HANDLER,
    ZONE_METRICS_HANDLER,
    METRICS_HANDLERS,
)
from daisyfl.utils.parameter import decode_ndarrays, ndarrays_to_parameters, parameters_to_ndarrays
from daisyfl.utils.logger import log
from .task_launcher import TaskLauncher
from daisyfl.common import NodeType

import numpy as np

class TaskManager():
    """Parse task configurations and manage tasks."""

    def __init__(
        self,
        task_launcher: TaskLauncher,
        node_type: NodeType,
    ) -> None:
        self.task_launcher: TaskLauncher = task_launcher
        self.type: NodeType = node_type
        if self.type == NodeType.MASTER:
            operator_key = [MASTER_SERVER_OPERATOR, MASTER_STRATEGY, MASTER_METRICS_HANDLER]
        else:
            operator_key = [ZONE_SERVER_OPERATOR, ZONE_STRATEGY, ZONE_METRICS_HANDLER]
        self.task_launcher.set_task_launcher_keys(operator_key)

    def receive_task(
        self, task_config: Dict, parameters: Optional[Parameters] = None
    )-> Tuple[Parameters, Report]:
        """This function is the task gateway of Daisy."""
        
        if parameters is None:
            parameters: Parameters = self._initialize_parameters(model_path=task_config[MODEL_PATH])
        
        if self.type == NodeType.MASTER:
            task_config = self.parse_task_spec(task_config=task_config)
        
        parameters, report = self.assign_task(parameters=parameters, task_config=task_config,)
        
        return parameters, report

    def parse_task_spec(
        self,
        task_config: Dict,
    ) -> Dict:
        """Parse declarative task configurations."""
        if not (task_config.__contains__(NUM_ROUNDS)):
            log(WARNING, "Use default num_rounds")
            task_config[NUM_ROUNDS] = 1
        
        if not (task_config.__contains__(ZONE_COMM_FREQUENCY)):
            log(WARNING, "Use default zone_comm_frequecy")
            task_config[ZONE_COMM_FREQUENCY] = 1

        if self.type == NodeType.ZONE:
            if not (task_config.__contains__(MIN_WAITING_TIME_ZONE)):
                log(WARNING, "Use default min_waiting_time_zone")
                task_config[MIN_WAITING_TIME_ZONE] = 10
        
        if not (task_config.__contains__(MIN_WAITING_TIME_MASTER)):
            log(WARNING, "Use default min_waiting_time_master")
            if not (task_config.__contains__(MIN_WAITING_TIME_ZONE)) or not (task_config.__contains__(ZONE_COMM_FREQUENCY)):
                task_config[MIN_WAITING_TIME_MASTER] = 10
            else:
                task_config[MIN_WAITING_TIME_MASTER] = task_config[MIN_WAITING_TIME_ZONE] * task_config[ZONE_COMM_FREQUENCY]
        
        if self.type == NodeType.MASTER:
            task_config[MIN_WAITING_TIME] = task_config[MIN_WAITING_TIME_MASTER]
        elif self.type == NodeType.ZONE:
            task_config[MIN_WAITING_TIME] = task_config[MIN_WAITING_TIME_ZONE]

        if not (task_config.__contains__(CURRENT_ROUND_MASTER)):
            log(WARNING, "Use default current_round_master")
            task_config[CURRENT_ROUND_MASTER] = 0

        if not (task_config.__contains__(CURRENT_ROUND_ZONE)):
            log(WARNING, "Use default current_round_zone")
            task_config[CURRENT_ROUND_ZONE] = 0
            
        task_config[CURRENT_ROUND] = task_config[CURRENT_ROUND_MASTER] * task_config[ZONE_COMM_FREQUENCY] + task_config[CURRENT_ROUND_ZONE]

        if not (task_config.__contains__(EVALUATE_INTERVAL)):
            log(WARNING, "Use default evaluate_interval_master")
            task_config[EVALUATE_INTERVAL] = task_config[NUM_ROUNDS]
        
        if not (task_config.__contains__(EVALUATE_INIT_MODEL_MASTER)):
            log(WARNING, "Use default evaluate_init_model_master")
            task_config[EVALUATE_INIT_MODEL_MASTER] = False

        if not (task_config.__contains__(OPERATORS)):
            log(WARNING, "No operator was specified. Use base operators.")
            task_config[OPERATORS] = {
		        MASTER_SERVER_OPERATOR: ["daisyfl.operator.base.server_logic", "ServerLogic"],
		        ZONE_SERVER_OPERATOR: ["daisyfl.operator.base.server_logic", "ServerLogic"],
                CLIENT_OPERATOR: ["daisyfl.operator.base.client_logic", "ClientLogic"],
	        }            
        if not (task_config.__contains__(STRATEGIES)):
            log(WARNING, "No strategy was specified. Use FedAvg.")
            task_config[STRATEGIES] = {
		        MASTER_STRATEGY: ["daisyfl.strategy", "FedAvg"],
		        ZONE_STRATEGY: ["daisyfl.strategy", "FedAvg"],
	        }
        if not (task_config.__contains__(METRICS_HANDLERS)):
            log(WARNING, "No MetricsHandler was specified. Use base MetricsHandler.")
            task_config[METRICS_HANDLERS] = {
		        MASTER_METRICS_HANDLER: ["daisyfl.metrics_handler", "MetricsHandler"],
		        ZONE_METRICS_HANDLER: ["daisyfl.metrics_handler", "MetricsHandler"],
	        }
        
        return task_config
    
    def assign_task(
        self,
        parameters: Parameters,
        task_config: Dict,
    )-> Tuple[Parameters, Report]:
        """
        Function to process a Task:
        1. Schedule the FL communication rounds for fitting or evaluating.
        2. Execute each individual round (called subtask).
        """
        if self.type == NodeType.MASTER:
            # MASTER
            ## Before the first round
            if task_config[EVALUATE_INIT_MODEL_MASTER]:
                task: Task = Task(config={
                    **task_config,
                    **{
                        EVALUATE: True,
                    }
                })
                parameters, report = self.assign_subtask(parameters=parameters, task=task)
            ## Fit and Evaluate
            for i in range(task_config[CURRENT_ROUND_MASTER], task_config[NUM_ROUNDS]):
                task: Task = Task(config={
                    **task_config,
                    **{
                        EVALUATE: False,
                    }
                })
                parameters, report = self.assign_subtask(parameters=parameters, task=task)
                task_config[CURRENT_ROUND_MASTER] = i + 1
                task_config[CURRENT_ROUND_ZONE] = 0
                task_config[CURRENT_ROUND] = task_config[CURRENT_ROUND_MASTER] * task_config[ZONE_COMM_FREQUENCY]
                if ((i + 1) != task_config[NUM_ROUNDS]) and ((i + 1) % task_config[EVALUATE_INTERVAL] == 0):
                    task: Task = Task(config={
                        **task_config,
                        **{
                            EVALUATE: True,
                        }
                    })
                    parameters, report = self.assign_subtask(parameters=parameters, task=task)
            ## After the last round
            task: Task = Task(config={
                **task_config,
                **{
                    EVALUATE: True,
                }
            })
            parameters, report = self.assign_subtask(parameters=parameters, task=task)
            return parameters, report
        else:
            # ZONE
            if task_config[EVALUATE]:
                # Evaluate global model
                task: Task = Task(config={
                    **task_config,
                })
                parameters, report = self.assign_subtask(parameters=parameters, task=task)
            else:
                # Fit zone model
                for i in range(task_config[CURRENT_ROUND_ZONE], task_config[ZONE_COMM_FREQUENCY]):
                    task: Task = Task(config={
                        **task_config,
                        **{
                            EVALUATE: False,
                        }
                    })
                    parameters, report = self.assign_subtask(parameters=parameters, task=task)
                    task_config[CURRENT_ROUND_ZONE] = i + 1
            if (not ("parameters" in locals())) or (not ("report" in locals())):
                log(ERROR, "Zone receive a reduncdant subtask. Please check the task configuration. {}".format(task_config))
                return Parameters(tensors=[], tensor_type=""), Report(config={})
            return parameters, report

    def assign_subtask(
        self,
        parameters: Parameters,
        task: Task,
    ) -> Tuple[Parameters, Report]:
        """Process a subtask."""
        if task.config[EVALUATE]:
            # evaluating task
            report: Report = self.task_launcher.evaluate_round(parameters, task)    
        else:
            # fitting task
            parameters, report = self.task_launcher.fit_round(parameters, task)
            if task.config[SAVE_MODEL]:
                self._save_parameters(parameters, task.config[MODEL_PATH],)
        return parameters, report

    # initial parameters
    def _initialize_parameters(self, model_path: str) -> Parameters:
        """Load the model parameters from the .npy file."""
        # FL Starting
        log(INFO, "Initializing global parameters")
        return ndarrays_to_parameters(list(np.load(model_path, allow_pickle=True)))

    def _save_parameters(self, parameters, path,):
        """Save the model parameters to a .npy file."""
        np.save(path, np.array(parameters_to_ndarrays(parameters), dtype=object))

