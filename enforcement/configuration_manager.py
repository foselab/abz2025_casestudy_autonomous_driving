import json
import pygame
import gymnasium as gym

import logging_manager

class ConfigurationManager:
    def __init__(self, config_file):
        self.logger = logging_manager.get_logger(__name__)
        with open(config_file) as json_file:
            self.json_data = json.load(json_file)

    def configure_env(self, run_enforcer):
        """
        Configure and return an HighwayEnv Environment
        """
        env = gym.make("highway-fast-v0", render_mode='human')
        # Parameters relative to rewards may be useful but are not strictly necessary for the execution of the tests
        env.configure({
            "lanes_count": 1 if self.json_data["single_lane"] else 3,
            "action": {
                "type": "DiscreteMetaAction",
                "target_speeds": [0,5,10,15,20,25,30,35,40]},
            "simulation_frequency": self.get_simulation_frequency(),
            "policy_frequency": self.get_policy_frequency(),
            "duration": self.get_duration(),
            "reward_speed_range": [0,40],
            "right_lane_reward": 0.0
        })
        if self.json_data["adversarial"]:
            env.configure({"collision_reward": 1,"high_speed_reward": 2})
            if not self.json_data["single_lane"]: # 3 lanes adversarial
                env.configure({"lane_change_reward": 0.5})
        else:
            env.configure({"collision_reward": -1, "high_speed_reward": 1})
            if not self.json_data["single_lane"]: # 3 lanes base
                env.configure({"right_lane_reward": 0.1})
        env.reset()
        caption = "Highway-env - " + ("with" if run_enforcer else "without") + " Enforcer"
        pygame.display.set_caption(caption)
        return env
    
    def get_policy_frequency(self):
        return self.json_data["simulation"]["policy_frequency"]
    
    def get_simulation_frequency(self):
        return self.json_data["simulation"]["simulation_frequency"]
    
    def get_duration(self):
        return self.json_data["simulation"]["duration"]
    
    def get_test_runs(self):
        return self.json_data["simulation"]["test_runs"]

    def get_policy(self):
        return "adversarial" if self.json_data["adversarial"] else "base"
    
    def is_single_lane(self):
        return self.json_data["single_lane"]
    
    def get_runtime_model(self):
        return self.json_data["enforcer"]["runtime_model"]
    
    def get_enforcer_params(self):
        enf_param = self.json_data["enforcer"]
        return enf_param["base_port"], enf_param["spec_path"], enf_param["runtime_model"]

    def get_logging_params(self):
        log_param = self.json_data["logging"]
        return log_param["level"], log_param["target_folder"]
    
    def write_to_xlsx(self):
        return self.json_data["experiments"]["write_to_xlsx"]
    
    def get_experiments_folder(self):
        return self.json_data["experiments"]["target_folder"]
    
    def log_configuration(self):
        self.logger.info("Configuration: ")
        self.logger.info(f"* Policy: {self.get_policy()}")
        self.logger.info(f"* Lane configuration: {'single lane' if self.is_single_lane() else 'multi lane'}")
        self.logger.info(f"* Runtime ASM model: {self.json_data['enforcer']['runtime_model']}")
        self.logger.info(f"* Number of test runs: {self.get_test_runs()}")
        self.logger.info(f"* Duration of each test run: {self.get_duration()} s")
        self.logger.info(f"* Policy frequency: {self.get_policy_frequency()} Hz")
        self.logger.info(f"* Simulation frequency: {self.get_simulation_frequency()} Hz")
    