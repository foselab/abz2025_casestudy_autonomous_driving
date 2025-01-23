import os
import sys

import logging_manager
import configuration_manager
import test_runner
import enforcer

CONFIG_FILE = "config.json"

run_enforcer = True if (len(sys.argv) == 2 and sys.argv[1] == "run_enforcer") else False

# Setup Configuration Manager
config_manager = configuration_manager.ConfigurationManager(CONFIG_FILE)

# Setup Logging
level, log_folder = config_manager.get_logging_params()
logging_manager.setup_logging(level, log_folder)
logger = logging_manager.get_logger(__name__)

logger.info("Loaded config.json - Starting execution")
config_manager.log_configuration()

# Obtain the path of the trained model
folder = ("single_" if config_manager.is_single_lane() else "") + config_manager.get_policy()
model_path = os.path.join("..", folder, "new", "trained_model")

# Configura the Environment (HighwayEnv)
env = config_manager.configure_env()

# Run the tests
test_runs = config_manager.get_test_runs()
if (run_enforcer):
    port, asm_path, asm_file_name = config_manager.get_enforcer_params()
    enf = enforcer.Enforcer(port, asm_path, asm_file_name)
    test_runner.test(model_path, env, enf, test_runs)
else:
    test_runner.test(model_path, env, None, test_runs)