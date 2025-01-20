import json
import gymnasium as gym

class ConfigurationManager:
    def __init__(self, config_file):
        with open(config_file) as json_file:
            self.json_data = json.load(json_file)
            
    def configure_env(self):
        """
        Configure and return an HighwayEnv Environment
        """
        env = gym.make("highway-fast-v0", render_mode='human')
        sim_param = self.json_data["simulation"]
        # Parameters relative to rewards may be useful but are not strictly necessary for the execution of the tests
        env.configure({
            "lanes_count": 1 if self.json_data["single_lane"] else 3,
            "action": {
                "type": "DiscreteMetaAction",
                "target_speeds": [0,5,10,15,20,25,30,35,40]},
            "simulation_frequency": sim_param["simulation_frequency"],
            "policy_frequency": sim_param["policy_frequency"],
            "duration": sim_param["duration"],
            "reward_speed_range": [0,40],
            "right_lane_reward": 0.0
        })
        if self.json_data["adversarial"]:
            env.configure({"collision_reward": 1,
                            "high_speed_reward": 2,})
            if not self.json_data["single_lane"]: # 3 lanes adversarial
                env.configure({"lane_change_reward": 0.5})
        else:
            env.configure({"collision_reward": -1,
                            "high_speed_reward": 1,})
            if not self.json_data["single_lane"]: # 3 lanes base
                env.configure({"right_lane_reward": 0.1})
        env.reset()
        return env
    
    def get_policy_frequency(self):
        return self.json_data["simulation"]["policy_frequency"]
    
    def get_test_runs(self):
        return self.json_data["simulation"]["test_runs"]

    def get_policy(self):
        return "adversarial" if self.json_data["adversarial"] else "base"
    
    def is_single_lane(self):
        return self.json_data["single_lane"]
    
    def get_enforcer_params(self):
        enf_param = self.json_data["enforcer"]
        return enf_param["base_port"], enf_param["spec_path"], enf_param["runtime_model"]

    def get_logging_params(self):
        log_param = self.json_data["logging"]
        return log_param["level"], log_param["target_folder"]
    