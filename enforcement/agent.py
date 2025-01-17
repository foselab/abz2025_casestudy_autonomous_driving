from stable_baselines3 import DQN
from highway_env.envs.common.action import DiscreteMetaAction

import env_observations_processor
import logging_manager

logger = logging_manager.get_logger(__name__)
REVERSED_ACTIONS = {value: key for key, value in DiscreteMetaAction.ACTIONS_ALL.items()}

def test(model_path, env, enforcer, test_runs):
    logger.info("Starting")
    
    execute_enforcer = enforcer != None

    model = DQN.load(model_path)

    crashes = 0
    if execute_enforcer:
        enforcer.upload_runtime_model()

    for _ in range(test_runs):

        if execute_enforcer:
            enforcer.begin_enforcement()

        state = env.reset()[0]
        done = False
        truncated = False
        while not done and not truncated:
            action = model.predict(state, deterministic=True)[0]

            if execute_enforcer:
                obs_config = env.observation_type
                x_self, v_self, x_front, v_front = env_observations_processor.process(obs_config, state)
                if x_front != float('inf'):
                    action_descritpion = DiscreteMetaAction.ACTIONS_ALL[int(action)]
                    action = REVERSED_ACTIONS[enforcer.sanitise_output(action_descritpion, x_self, v_self, x_front, v_front)]

            next_state, reward, done, truncated, info = env.step(action)

            #if execute_enforcer:
                #enforcer.log_step_info(env.observation_type, next_state, reward, info)

            state = next_state
            env.render()

            if info and info['crashed']:
                crashes += 1
        

        #TODO: mettere le metriche qui
        if execute_enforcer:
            enforcer.end_enforcement()

    if execute_enforcer:
        enforcer.delete_runtime_model()
    env.close()
