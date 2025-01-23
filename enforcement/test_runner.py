import time
from stable_baselines3 import DQN
from highway_env.envs.common.action import DiscreteMetaAction

import observation_processor
import logging_manager

logger = logging_manager.get_logger(__name__)
REVERSED_ACTIONS = {value: key for key, value in DiscreteMetaAction.ACTIONS_ALL.items()}

def test(model_path, env, enforcer, test_runs):
    """
    Run a series of tests

    Parameters:
        model_path (str): Path to the trained AI model.
        env (gym.Env): The simulation environment in which the model will be tested.
        enforcer (Enforcer or None): An optional enforcement module to validate and correct actions.
        test_runs (int): Number of test episodes to run.
        policy_frequency (int): The frequency at which the model takes actions (Hz).

    Returns:
        None
    """
        
    execute_enforcer = enforcer != None
    policy_frequency = env.config["policy_frequency"]

    model = DQN.load(model_path)

    crashes = 0
    total_km = 0
    if execute_enforcer:
        start_time = time.perf_counter()
        enforcer.upload_runtime_model()
        upload_delay = (time.perf_counter() - start_time) * 1000

    for i in range(test_runs):
        logger.info("--Starting new test run--")
        test_run_start = time.perf_counter()
        km = 0
        n_step = 0
        if execute_enforcer:
            sanitisation_delay = 0
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

            # Read the obesrvation
            x_self, v_self, x_front, v_front = observation_processor.process(env, state)

            if execute_enforcer:
                # Do not execute the enforcer if there is no front vehicle
                if x_front == float('inf'):
                    logger.info("Enforcer not executed: no front vehicle observed")
                    logger.info(f"Action: {action_descritpion}")
                else:
                    # Run the enforcer to sanitise the action predicted by the agent
                    start_time = time.perf_counter()
                    enforced_action = enforcer.sanitise_output(action_descritpion, x_self, v_self, x_front, v_front)
                    sanitisation_delay += (time.perf_counter() - start_time) * 1000
                    # Change the action if the enforcer returns a new different one
                    if enforced_action != None: 
                        action = REVERSED_ACTIONS[enforced_action]
                        enforcer_interventions += 1
            else:
                logger.info(f"Action: {action_descritpion}")

            # Run the step on the environment
            next_state, reward, done, truncated, info = env.step(action)

            # Compute the metrics
            if info and info['crashed']:
                crashes += 1
                logger.info("Test run terminated - ego vehicle crashed")
            km += (v_self*(1/policy_frequency))/1000 
            n_step += 1

            # Update the state (observation) and render the environment for the next step
            state = next_state
            env.render()

        total_km += km

        if execute_enforcer:
            start_time = time.perf_counter()
            enforcer.end_enforcement()
            stop_delay = (time.perf_counter() - start_time) * 1000
            logger.info("Enforcer delays:")
            logger.info(f"* Start delay: {start_delay:.2f}ms")
            logger.info(f"* Total sanitisation delay: {sanitisation_delay:.2f}ms")
            logger.info(f"* Stop delay: {stop_delay:.2f}ms")
            logger.info(f"Number of enforcer interventions: {enforcer_interventions} (out of {n_step})")

        test_execution_time = (time.perf_counter() - test_run_start) * 1000
        effective_duration = int(n_step/policy_frequency)
        logger.info(f"Effective Duration: {effective_duration} simulation seconds")
        logger.info(f"Test run {i} completed in {test_execution_time:.2f}ms: {km:.2f}km traveled")
        logger.info("")

    logger.info(f"Global metrics on {test_runs} test runs:")
    logger.info(f"* Crashes: {crashes} / {test_runs} runs, ({crashes / test_runs * 100:.2f}%)")
    logger.info(f"* Average distance traveled: {total_km / test_runs:.2f}km")

    if execute_enforcer:
        start_time = time.perf_counter()
        enforcer.delete_runtime_model()
        delete_delay = (time.perf_counter() - start_time) * 1000
        logger.info(f"Upload model delay: {upload_delay:.2f}ms")
        logger.info(f"Delete model delay: {delete_delay:.2f}ms")

    env.close()
