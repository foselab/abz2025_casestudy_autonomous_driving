import os
import requests
import subprocess
import time
from highway_env.envs.common.action import DiscreteMetaAction

import logging_manager

class Enforcer:    
    def __init__(self, base_port, asm_base_path, asm_name):
        """
        Initialize the Enforcer class and determine the local domain.
        """
        self.logger = logging_manager.get_logger(__name__)
        self.asm_name = asm_name
        self.stdl_name = "StandardLibrary.asm"
        self.ltl_name = "LTLLibrary.asm"
        libraries_base_path = os.path.join(asm_base_path, "..", "libraries")
        self.asm_path = os.path.join(asm_base_path, self.asm_name)
        self.stdl_path = os.path.join(libraries_base_path, self.stdl_name)
        self.ltl_path = os.path.join(libraries_base_path, self.ltl_name)
        self.base_port = base_port
        self.api_base_url = self._resolve_api_endpoint()
        self.exec_id = None
        self.logger.info(f"Enforcer initialized with domain: {self.api_base_url}")
        self.logger.info(f"Runtime model: {self.asm_name}")
        self.logger.info("")

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
                        return f"http://{line.split()[2]}:{self.base_port}/"
            except subprocess.SubprocessError as e:
                self.logger.error(f"Failed to determine WSL IP: {e}")
        return f"http://localhost:{self.base_port}/"

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
            self.logger.error(f"HTTP Request timed out: {e}")
            raise
        except requests.RequestException as e:
            self.logger.error(f"HTTP Request failed: {e}")
            raise

    def _upload_file(self, endpoint, file_path):
        """
        Helper method to upload a file to a specific endpoint.
        """
        with open(file_path, "rb") as file:
            files = {"file": file}
            self._send_request("POST", endpoint, files=files)
        self.logger.info(f"Uploaded file: {file_path}")

    def upload_runtime_model(self):
        """
        Upload the model and standard library if not already present.
        """
        try:
            self._upload_file("upload-model", self.asm_path)
            response = self._send_request("GET", "model-list")
            libraries = response.json().get("libraries")
            if self.stdl_name not in libraries:
                self._upload_file("upload-library", self.stdl_path)
            if self.ltl_name not in libraries:
                self._upload_file("upload-library", self.ltl_path)
        except Exception as e:
            self.logger.error(f"Failed to upload model or library: {e}")
            raise

    def delete_runtime_model(self):
        """
        Delete the model from the server and eventually the LTL library.
        """
        try:
            self._send_request("DELETE", "delete-model", params={"name": self.asm_name})
            self.logger.info(f"Model deleted: {self.asm_name}")    
            response = self._send_request("GET", "model-list")       
            libraries = response.json().get("libraries")
            if self.ltl_name in libraries:
                self._send_request("DELETE", "delete-library", params={"name": self.ltl_name})
        except Exception as e:
            self.logger.error(f"Failed to delete model: {e}")
            raise
    
    def begin_enforcement(self):
        """
        Start a new execution of the ASM.
        """
        try:
            response = self._send_request("POST", "start", params={"name": self.asm_name})
            self.exec_id = response.json()["id"]
            self.logger.info(f"Execution started with ID: {self.exec_id}")
        except Exception as e:
            self.logger.error(f"Failed to start execution: {e}")
            raise

    def end_enforcement(self):
        """
        Stop the execution of the ASM.
        """
        try:
            self._send_request("DELETE", "stop-model", params={"id": str(self.exec_id)})
            self.logger.info(f"Execution stopped for ID: {self.exec_id}")
        except Exception as e:
            self.logger.error(f"Failed to stop execution: {e}")
            raise

    def sanitise_output(self, input_action, x_self, v_self, x_front, v_front, right_lane_free):
        """
        Perform a step on the ASM and read the action (i.e. output sanitisation).
        """
        endpoint = "step"
        json_data = {
            "id": self.exec_id,
            "monitoredVariables": {
                "inputAction": input_action,
                "x_self": x_self,
                "v_self": v_self,
                "x_front": x_front,
                "v_front": v_front}
        }
        if self.asm_name == "SafetyEnforcerKeepRight.asm":
            json_data["monitoredVariables"]["rightLaneFree"] = "true" if right_lane_free else "false"
        try:
            start_time = time.perf_counter()
            response = self._send_request("PUT", endpoint, json=json_data)
            delay = (time.perf_counter() - start_time) * 1000
            self.logger.info(f"ASM step performed for ID {self.exec_id} with delay {delay:.2f} ms")
            if not response.json()["runOutput"]["outvalues"]: # outAction not set (should never happen)
                self.logger.error("The Enforcer returned no outAction but should always return something")
                self.logger.info(f"Input Action: {input_action}")
                return None
            enforced_action = response.json()["runOutput"]["outvalues"]["outAction"]
            if enforced_action == input_action:
                self.logger.info("Enforcer not applied - keeping input action")
                self.logger.info(f"Input Action: {input_action}")
                return None
            else:
                self.logger.info("Enforcer applied - changing action")
            self.logger.info(f"Input Action: {input_action}")
            self.logger.info(f"After Safety Enforcement: {enforced_action}")
            return enforced_action
        except Exception as e:
            self.logger.error("ASM step execution failed: %s", e)
            raise