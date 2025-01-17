import os

import logging_manager
import configuration_manager
import agent
import enforcer

cm = configuration_manager.ConfigurationManager("config.json")

level, log_folder = cm.get_logging_params()
logging_manager.setup_logging(level, log_folder)
logger = logging_manager.get_logger(__name__)

logger.info("Loaded config.json - Starting execution")

test_runs = cm.get_test_runs()

folder = ("single_" if cm.is_single_lane() else "") + cm.get_policy()
model_path = os.path.join("..", folder, "new", "trained_model")

env = cm.configure_env()
if (cm.run_enforcer()):
    port, asm_path, asm_file_name = cm.get_enforcer_params()
    enf = enforcer.Enforcer(port, asm_path, asm_file_name)
    agent.test(model_path, env, enf, test_runs)
    delay = enf.get_maximum_delay()
    logger.info("Maximum delay introduced by the enforcer: %i ms", delay)
else:
    agent.test(model_path, env, None, test_runs)