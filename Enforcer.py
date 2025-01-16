import os
import requests
import subprocess
import time
import logging
import numpy
from highway_env.envs.common.action import DiscreteMetaAction

class Enforcer:
    LOG_FILE = "enforcer.log"
    LOG_LEVEL = logging.INFO
    BASE_PORT = 8080
    DEFAULT_BASE_FILE_PATH = "."
    DEFAULT_ASM_FILE_NAME = "SafetyController.asm"
    DEFAULT_STDL_FILE_NAME = "StandardLibrary.asm"
    
    def __init__(self, base_path=None, asm_name=None, stdl_name=None):
        """
        Initialize the Enforcer class and determine the local domain.
        """
        numpy.set_printoptions(precision=2, suppress=True)
        self._configure_logging()
        base_path = base_path or self.DEFAULT_BASE_FILE_PATH
        self.asm_name = asm_name or self.DEFAULT_ASM_FILE_NAME
        self.stdl_name = stdl_name or self.DEFAULT_STDL_FILE_NAME
        self.asm_path = f"{base_path}/{self.asm_name}"
        self.stdl_path = f"{base_path}/{self.stdl_name}"
        self.api_base_url = self._resolve_api_endpoint()
        self.exec_id = None
        self.max_enforcement_delay = 0
        logging.info("Enforcer initialized with domain: %s", self.api_base_url)
        logging.info("Runtime model: %s", self.asm_name)
        logging.info("")

    def _configure_logging(self):
        """
        Configure the logging.
        """
        logging.basicConfig(
            level=self.LOG_LEVEL,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.LOG_FILE),
            ]
        )

    def _resolve_api_endpoint(self):
        """
        Determine the local domain dynamically, especially for WSL environments.
        """
        if "WSL_INTEROP" in os.environ:
            try:
                result = subprocess.run(
                    ["ip", "route"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                '''
                Example of 'ip route' command on WSL:
                    default via 172.25.16.1 dev eth0 proto kernel
                    172.25.16.0/20 dev eth0 proto kernel scope link src 172.25.31.78
                '''
                for line in result.stdout.splitlines():
                    if "default" in line:
                        return f"http://{line.split()[2]}:{self.BASE_PORT}/"
            except subprocess.SubprocessError as e:
                logging.error("Failed to determine WSL IP: %s", e)
        return f"http://localhost:{self.BASE_PORT}/"

    def _send_request(self, method, endpoint, **kwargs):
        """
        A helper method for sending HTTP requests with error handling.
        """
        url = self.api_base_url + endpoint
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response
        except requests.Timeout as e:
            logging.error("HTTP Request timed out: %s", e)
            raise
        except requests.RequestException as e:
            logging.error("HTTP Request failed: %s", e)
            raise

    def _upload_file(self, endpoint, file_path):
        """
        Helper method to upload a file to a specific endpoint.
        """
        with open(file_path, "rb") as file:
            files = {"file": file}
            self._send_request("POST", endpoint, files=files)
        logging.info("Uploaded file: %s", file_path)

    def upload_runtime_model(self):
        """
        Upload the model and standard library if not already present.
        """
        try:
            self._upload_file("upload-model", self.asm_path)
            response = self._send_request("GET", "model-list")
            libraries = response.json().get("libraries")
            if "StandardLibrary.asm" not in libraries:
                self._upload_file("upload-library", self.stdl_path)
        except Exception as e:
            logging.error("Failed to upload model or library: %s", e)
            raise

    def delete_runtime_model(self):
        """
        Delete the model from the server.
        """
        try:
            self._send_request("DELETE", "delete-model", params={"name": self.asm_name})
            logging.info("Model deleted: %s", self.asm_name)
        except Exception as e:
            logging.error("Failed to delete model: %s", e)
            raise
    
    def begin_enforcement(self):
        """
        Start a new execution of the ASM.
        """
        try:
            response = self._send_request("POST", "start", params={"name": self.asm_name})
            self.exec_id = response.json()["id"]
            logging.info("Execution started with ID: %s", self.exec_id)
        except Exception as e:
            logging.error("Failed to start execution: %s", e)
            raise

    def end_enforcement(self):
        """
        Stop the execution of the ASM.
        """
        try:
            self._send_request("DELETE", "stop-model", params={"id": str(self.exec_id)})
            logging.info("Execution stopped for ID: %s", self.exec_id)
            logging.info("Maximum delay introduced by the enforcer: %i ms", self.max_enforcement_delay)
        except Exception as e:
            logging.error("Failed to stop execution: %s", e)
            raise


    def sanitise_output(self, input_action):
        """
        Perform a step on the ASM and read the action (i.e. output sanitisation).
        """
        endpoint = "step"
        json_data = {
            "id": self.exec_id,
            "monitoredVariables": {"inputAction": str(input_action)},
        }
        start_time = time.perf_counter()
        try:
            response = self._send_request("PUT", endpoint, json=json_data)
            delay = (time.perf_counter() - start_time) * 1000
            self.max_enforcement_delay = max(self.max_enforcement_delay, delay)
            enforced_action = int(response.json()["runOutput"]["outvalues"]["outputAction"])
            logging.info("ASM step performed for ID %s with delay %i ms", self.exec_id, delay)
            actions_description = DiscreteMetaAction.ACTIONS_ALL
            logging.info(f"Input Action: {input_action} ({actions_description[int(input_action)]})")
            logging.info(f"After Safety Enforcement: {enforced_action} ({actions_description[enforced_action]})")
            return enforced_action
        except Exception as e:
            logging.error("ASM step execution failed: %s", e)
            raise

    def _extract_rear_and_front(self, observations):
        x_rear = float('-inf')
        vx_rear = None
        x_front = float('inf')
        vx_front = None
        for observation in observations[1:]:
            x = observation[1]
            vx = observation[3]
            if x < 0 and x > x_rear:
                x_rear, vx_rear = x, vx
            elif x > 0 and x < x_front:
                x_front, vx_front = x, vx
        return x_rear, vx_rear, x_front, vx_front 
    
    def _extract_ego(self, observations):
        return observations[0][1], observations[0][3] 

    def log_step_info(self, next_state, reward, info):
        """
        Log info about a step on the environment.
        """
        '''
                            Presence    x      y       vx      vy
        ------------------------------------------------------------
        ControlledVehicle     1.0       0.89    0.50    0.31    0.0
        Vehicle_2             1.0       0.09   -0.50   -0.04    0.0
        Vehicle_3             1.0       0.21    0.00   -0.02    0.0
        Vehicle_4             1.0       0.33    0.00   -0.04    0.0
        Vehicle_5             1.0       0.43   -0.25   -0.04    0.0
        ----
        [[ 1.    0.89    0.50    0.31    0.  ]
        [ 1.    0.09   -0.50   -0.04  0.  ]
        [ 1.    0.21    0.00   -0.02  0.  ]
        [ 1.    0.33    0.00   -0.04  0.  ]
        [ 1.    0.43   -0.25   -0.04  0.  ]]
        '''
        x_rear, vx_rear, x_front, vx_front = self._extract_rear_and_front(next_state)
        x_ego, vx_ego = self._extract_ego(next_state)
        if x_rear == float('-inf'):
            x_rear = vx_rear = "N/A"
        if x_front == float('-inf'):
            x_front = vx_front = "N/A"
        speed = info.get("speed", "N/A")
        crashed = info.get("crashed", "N/A")
        rewards = info.get("rewards", "N/A")
        logging.info("Next state (observations):\n %s", next_state)
        logging.info("Other vehicles information:")
        logging.info("*Rear vehicle x: %s, vx: %s", x_rear, vx_rear)
        logging.info("*Front vehicle x: %s, vx: %s", x_front, vx_front)
        logging.info("Ego vehicle information:")
        logging.info("*Ego vehicle x: %s, vx: %s", x_ego, vx_ego)
        logging.info("*Speed: %s", speed)
        logging.info("*Crashed: %s", crashed)
        logging.info("*Reward: %s", reward)
        logging.info("*Rewards: %s", rewards)
        logging.info("-"*30)
