import os
import sys
import uuid

import logging_manager
import test_runner
from configuration_manager import ConfigurationManager
from enforcer import Enforcer
from xlsx_writer import ExcelWriter

CONFIG_FILE = "config.json"

run_enforcer = True if (len(sys.argv) == 2 and sys.argv[1] == "run_enforcer") else False

# Setup Configuration Manager
config_manager = ConfigurationManager(CONFIG_FILE)

# Setup Logging
level, log_folder = config_manager.get_logging_params()
logging_manager.setup_logging(level, log_folder)
logger = logging_manager.get_logger(__name__)

logger.info("Loaded config.json - Starting execution")
config_manager.log_configuration()

# Initialize the xlsx writer
write_to_xlsx = config_manager.write_to_xlsx()
if write_to_xlsx:
    config_sub_row = [
        uuid.uuid4(),
        config_manager.get_policy_frequency(),
        config_manager.get_policy(),
        "single" if config_manager.is_single_lane() else "multi",
        run_enforcer,
        "NaN" if not run_enforcer else config_manager.get_enforcer_rules() # There is no check that the actual rules used in the ASM match
    ]
    xlsx_writer = ExcelWriter(config_manager.get_experiments_folder(), config_sub_row)

# Obtain the path of the trained model
folder = ("single_" if config_manager.is_single_lane() else "") + config_manager.get_policy()
model_path = os.path.join("..", folder, "new", "trained_model")

# Configura the Environment (HighwayEnv)
env = config_manager.configure_env()

# Run the tests
test_runs = config_manager.get_test_runs()
if (run_enforcer):
    port, asm_path, asm_file_name = config_manager.get_enforcer_params()
    enf = Enforcer(port, asm_path, asm_file_name)
    test_runner.test(model_path, env, enf, test_runs, xlsx_writer if write_to_xlsx else None)
else:
    test_runner.test(model_path, env, None, test_runs, xlsx_writer if write_to_xlsx else None)

# Write to the excel file
if write_to_xlsx:
    xlsx_writer.write_xlsx()