import json
import gymnasium as gym

class ConfigurationManager:
    def __init__(self, config_file):
        with open(config_file) as json_file:
            self.json_data = json.load(json_file)
            
    def configure_env(self):
        env = gym.make("highway-fast-v0", render_mode='human')
        sim_param = self.json_data["simulation"]
        env.configure({
            "lanse_count": 1 if self.json_data["single_lane"] else 3,
            "action": {
                "type": "DiscreteMetaAction",
                "target_speeds": [0,5,10,15,20,25,30,35,40]},
            "simulation_frequency": sim_param["simulation_frequency"],
            "policy_frequency": sim_param["policy_frequency"],
            "duration": sim_param["duration"]
        })
        env.reset()
        return env

    def get_test_runs(self):
        return self.json_data["simulation"]["test_runs"]

    def get_policy(self):
        return "adversarial" if self.json_data["adversarial"] else "base"
    
    def is_single_lane(self):
        return self.json_data["single_lane"]

    def run_enforcer(self):
        return self.json_data["enforcement"]
    
    def get_enforcer_params(self):
        enf_param = self.json_data["enforcer"]
        return enf_param["base_port"], enf_param["spec_path"], enf_param["runtime_model"]

    def get_logging_params(self):
        log_param = self.json_data["logging"]
        return log_param["level"], log_param["target_folder"]