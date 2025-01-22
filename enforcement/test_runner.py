from stable_baselines3 import DQN
from highway_env.envs.common.action import DiscreteMetaAction

import observation_processor
import logging_manager

logger = logging_manager.get_logger(__name__)
REVERSED_ACTIONS = {value: key for key, value in DiscreteMetaAction.ACTIONS_ALL.items()}

def test(model_path, env, enforcer, test_runs, policy_frequency):
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

    model = DQN.load(model_path)

    crashes = 0
    total_km = 0
    if execute_enforcer:
        enforcer.upload_runtime_model()

    for i in range(test_runs):
        km = 0
        n_step = 0
        if execute_enforcer:
            enforcer_interventions = 0 # Number of step in which the enforcer changed the input action to a different action
            enforcer.begin_enforcement()
        state = env.reset()[0]
        done = False
        truncated = False

        while not done and not truncated:
            # Use the AI model to predict the next action
            action = model.predict(state, deterministic=True)[0]
            action_descritpion = DiscreteMetaAction.ACTIONS_ALL[int(action)]

            # Read the obesrvation
            obs_config = env.observation_type
            x_self, v_self, x_front, v_front = observation_processor.process(obs_config, state)

            if execute_enforcer:
                # Do not execute the enforcer if there is no front vehicle
                if x_front == float('inf'):
                    logger.info("Enforcer not executed: no front vehicle observed")
                    logger.info(f"Action: {action_descritpion}")
                else:
                    # Run the enforcer to sanitise the action predicted by the agent
                    enforced_action = enforcer.sanitise_output(action_descritpion, x_self, v_self, x_front, v_front)
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
        logger.info(f"Test run {i} completed: {km:.2f} km traveled")
        if execute_enforcer:
            logger.info(f"The Enforcer changed input action {enforcer_interventions} times out of {n_step} step")
            enforcer.end_enforcement()

    logger.info(f"Crashes: {crashes} / {test_runs} runs, ({crashes / test_runs * 100:.2f}%)")
    logger.info(f"Average distance traveled: {total_km / test_runs:.2f}km")

    #if execute_enforcer:
    #    enforcer.delete_runtime_model()

    env.close()
