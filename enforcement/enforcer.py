import time
from highway_env.envs.common.action import DiscreteMetaAction

import logging_manager
from rest_client import RestClient

class Enforcer(RestClient):    
    def __init__(self, base_port, asm_name):
        """
        Initialize the Enforcer class.
        """
        super().__init__(base_port)
        self.logger = logging_manager.get_logger(__name__)
        self.asm_name = asm_name
        self.exec_id = None
    
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