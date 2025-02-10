import os
import sys
import uuid
import time
from stable_baselines3 import DQN
from highway_env.envs.common.action import DiscreteMetaAction

import logging_manager
from configuration_manager import ConfigurationManager
from enforcer import Enforcer
from model_uploader import ModelUploader
from experiment_data_exporter import ExperimentDataExporter
from observation_processor import ObservationProcessor

def run(model_path, env, enforcer:Enforcer, model_uploader:ModelUploader, test_runs, data_exporter:ExperimentDataExporter):
    """
    Run a series of tests for the Autonomous Driving System, with or without enforcement

    Parameters:
        model_path (str): Path to the trained AI model.
        env (gym.Env): The simulation environment in which the model will be tested.
        enforcer (Enforcer or None): An optional enforcement module to validate and correct actions.
        model_uploader(ModelUploader or None): An optional module for uploading the asm spec and the asm libraries.
        test_runs (int): Number of test episodes to run.
        data_exporter (ExperimentDataExporter or None): An optional already initialized experiment data exporter

    Returns:
        None
    """
        
    execute_enforcer = enforcer != None
    write_to_xslx = data_exporter != None
    policy_frequency = env.config["policy_frequency"]

    REVERSED_ACTIONS = {value: key for key, value in DiscreteMetaAction.ACTIONS_ALL.items()}

    model = DQN.load(model_path)

    crashes = 0
    total_traveled_distance = 0
    if execute_enforcer:
        start_time = time.perf_counter()
        model_uploader.upload_runtime_model()
        upload_delay = (time.perf_counter() - start_time) * 1000

    for i in range(test_runs):
        logger.info("--Starting new test run--")
        test_run_start = time.perf_counter()
        crash = False
        traveled_distance = 0
        traveled_distance_on_right_lane = 0
        n_step = 0
        if execute_enforcer:
            total_sanitisation_delay = 0
            max_sanitisation_delay = 0
            enforcer_interventions = 0 # Number of step in which the enforcer changed the input action to a different action
            start_time = time.perf_counter()
            enforcer.begin_enforcement()
            start_delay = (time.perf_counter() - start_time) * 1000
        state = env.reset()[0]
        done = False
        truncated = False

        while not done and not truncated:
            logger.info("--Executing new step--")
            # Use the AI model to predict the next action
            action = model.predict(state, deterministic=True)[0]
            action_descritpion = DiscreteMetaAction.ACTIONS_ALL[int(action)]

            # Do not execute the enforcer if the controlled vehicle is changing lane
            # (wait until it ends the maneuver)
            observation_processor = ObservationProcessor(env, state)
            
            if observation_processor.is_controlled_vehicle_changing_lane():
                logger.info("The controlled vehicle is changing lane, the enforcer will not be executed until the maneuver is completed")
                logger.info(f"Action: {action_descritpion}")
            else:
                x_self, v_self, x_front, v_front, right_lane_free = observation_processor.process()

                # Compute the minimum safety distance (just for logging)
                rho = 1/policy_frequency
                v_max = 40
                a_max = 0 if v_self == v_max else 5
                b_max = 5 
                b_min = 3
                l_vehicle = 5
                if x_front != float("inf"):
                    actual_distance = x_front - x_self - l_vehicle
                    dRSS =  max(0, v_self*rho + \
                            (1/2)*a_max*rho**2 + \
                            ((v_self + rho*a_max)**2)/(2*b_min) - \
                            (v_front**2)/(2*b_max))
                    logger.info(f"Distance to front vehicle: {actual_distance:.2f}m")
                    logger.info(f"Minimum safety distance: {dRSS:.2f}m")
                else:
                    logger.info(f"Minimum safety distance can not be computed: no front vehicle observed")
                # If the enforcer is running, try to sanitise the output
                if execute_enforcer:
                    # Do not execute the enforcer if there is no front vehicle
                    if x_front == float('inf'):
                        logger.info("Enforcer not executed: no front vehicle observed")
                        logger.info(f"Action: {action_descritpion}")
                    else:
                        # Run the enforcer to sanitise the action predicted by the agent
                        start_time = time.perf_counter()
                        enforced_action = enforcer.sanitise_output(action_descritpion, x_self, v_self, x_front, v_front, right_lane_free)
                        sanitisation_delay = (time.perf_counter() - start_time) * 1000
                        max_sanitisation_delay = max(max_sanitisation_delay, sanitisation_delay)
                        total_sanitisation_delay += sanitisation_delay
                        # Change the action if the enforcer returns a new different one
                        if enforced_action != None: 
                            action = REVERSED_ACTIONS[enforced_action]
                            enforcer_interventions += 1

                    '''
                    logger.error(f"set inputAction := {action_descritpion};")
                    logger.error(f"set x_front := {x_front};")
                    logger.error(f"set x_self := {x_self};")
                    logger.error(f"set v_front := {v_front};")
                    logger.error(f"set v_self := {v_self};")
                    logger.error(f"set right_lane_free := {right_lane_free};")
                    logger.error(f"step")
                    logger.error(f"check currentAgentAction = {action_descritpion};")
                    logger.error(f"check outAction = {enforced_action};")
                    logger.error(f"check dRSS_contr = {dRSS};")
                    logger.error(f"check actual_distance_contr = {actual_distance};")
                    '''
                else:
                    logger.info(f"Action: {action_descritpion}")

            # Run the step on the environment
            next_state, reward, done, truncated, info = env.step(action)

            # Compute the metrics
            if info and info['crashed']:
                crashes += 1
                crash = True
                logger.info("Test run terminated - ego vehicle crashed")
            step_traveled_distance = (v_self*(1/policy_frequency))/1000
            traveled_distance += step_traveled_distance
            if observation_processor.is_controlled_vehicle_on_right_lane():
                traveled_distance_on_right_lane += step_traveled_distance
            n_step += 1

            # Update the state (observation) and render the environment for the next step
            state = next_state
            env.render()

        total_traveled_distance += traveled_distance

        # Stop the execution of the runtime model
        if execute_enforcer:
            start_time = time.perf_counter()
            enforcer.end_enforcement()
            stop_delay = (time.perf_counter() - start_time) * 1000
            logger.info("Enforcer delays:")
            logger.info(f"* Start delay: {start_delay:.2f}ms")
            logger.info(f"* Total sanitisation delay: {total_sanitisation_delay:.2f}ms (max {max_sanitisation_delay:.2f}ms)")
            logger.info(f"* Stop delay: {stop_delay:.2f}ms")
            logger.info(f"Number of enforcer interventions: {enforcer_interventions} (out of {n_step})")

        test_execution_time = (time.perf_counter() - test_run_start) * 1000
        effective_duration = int(n_step/policy_frequency)
        logger.info(f"Test run {i} completed in {test_execution_time:.2f}ms:")
        logger.info(f"* Effective Duration: {effective_duration} simulation seconds")
        logger.info(f"* Traveled distance: {traveled_distance:.2f}km")
        logger.info(f"* Traveled distance on right lane: {traveled_distance_on_right_lane:.2f}km")
        logger.info("")

        # Add the row relative to the test run to the table
        if write_to_xslx:
            row = [
                crash,
                traveled_distance_on_right_lane,
                traveled_distance,
                effective_duration,
                "NaN" if not execute_enforcer else enforcer_interventions,
                "NaN" if not execute_enforcer else start_delay,
                "NaN" if not execute_enforcer else stop_delay,
                "NaN" if not execute_enforcer else total_sanitisation_delay,
                "NaN" if not execute_enforcer else max_sanitisation_delay,
                test_execution_time
            ]
            data_exporter.add_row(row)

    logger.info(f"Global metrics on {test_runs} test runs:")
    logger.info(f"* Crashes: {crashes} / {test_runs} runs, ({crashes / test_runs * 100:.2f}%)")
    logger.info(f"* Average distance traveled: {total_traveled_distance / test_runs:.2f}km")

    # Delete the runtime models
    if execute_enforcer:
        start_time = time.perf_counter()
        model_uploader.delete_runtime_model()
        delete_delay = (time.perf_counter() - start_time) * 1000
        logger.info(f"Upload model delay: {upload_delay:.2f}ms")
        logger.info(f"Delete model delay: {delete_delay:.2f}ms")

    env.close()

if __name__ == '__main__':
    CONFIG_FILE = "config.json"

    run_enforcer = True if (len(sys.argv) == 2 and sys.argv[1] == "run_enforcer") else False

    # Setup Configuration Manager
    config_manager = ConfigurationManager(CONFIG_FILE)

    # Setup Logging
    execution_id = uuid.uuid4()
    level, log_folder = config_manager.get_logging_params()
    logging_manager.setup_logging(level, log_folder, execution_id)
    logger = logging_manager.get_logger(__name__)

    logger.info(f"Loaded config.json - Starting execution with id {execution_id}")
    config_manager.log_configuration()

    # Initialize the xlsx writer
    write_to_xlsx = config_manager.write_to_xlsx()
    if write_to_xlsx:
        config_sub_row = [
            execution_id,
            config_manager.get_policy_frequency(),
            config_manager.get_policy(),
            "single" if config_manager.is_single_lane() else "multi",
            run_enforcer,
            "NaN" if not run_enforcer else config_manager.get_runtime_model()
        ]
        data_exporter = ExperimentDataExporter(config_manager.get_experiments_folder(), config_sub_row)

    # Obtain the path of the trained model
    folder = ("single_" if config_manager.is_single_lane() else "") + config_manager.get_policy()
    model_path = os.path.join("..", folder, "new", "trained_model")

    # Configura the Environment (HighwayEnv)
    env = config_manager.configure_env()

    # Run the tests
    test_runs = config_manager.get_test_runs()
    if (run_enforcer):
        port, asm_path, asm_file_name = config_manager.get_enforcer_params()
        enforcer = Enforcer(port, asm_file_name)
        model_uploader = ModelUploader(port, asm_path, asm_file_name)
        run(model_path, env, enforcer, model_uploader, test_runs, data_exporter if write_to_xlsx else None)
    else:
        run(model_path, env, None, None, test_runs, data_exporter if write_to_xlsx else None)

    # Write to the excel file
    if write_to_xlsx:
        data_exporter.write_xlsx()
