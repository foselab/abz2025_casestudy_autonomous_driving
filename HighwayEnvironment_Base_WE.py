import warnings
import os
import sys

import gymnasium as gym
import highway_env
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import CheckpointCallback

import Enforcer

save_base_path = "base"

# Configuration (default values in parenthesis)
env = gym.make("highway-fast-v0", render_mode='human')
env.configure({
    "action": {
        "type": "DiscreteMetaAction",
        "target_speeds": [0,5,10,15,20,25,30,35,40]},
    "lanes_count": 3,  # (4)
    "collision_reward": -1, # (-1)
    "right_lane_reward": 0.1, # (0.1),
    "reward_speed_range": [0, 40],
    "high_speed_reward": 1,
})
# env.configure({
#     "lanes_count": 3,  # (4)
#     "vehicles_count": 40,  # (50)
#     "duration": 40,  # (40) [s]
#
#     # (-1) The reward received when colliding with a vehicle.
#     "collision_reward": -1,
#     # ([20, 30]) [m/s] The reward for high speed is mapped linearly from this range to [0, HighwayEnv.HIGH_SPEED_REWARD].
#     "reward_speed_range": [20, 30],
#     # (0.1) The reward received when driving on the right-most lanes, linearly mapped to
#     "right_lane_reward": 0.2, # (0.1)
#     # zero for other lanes.
#     # (0.4) The reward received when driving at full speed, linearly mapped to zero for
#     "high_speed_reward": 0.5, # (0.4)
#     # lower speeds according to config["reward_speed_range"].
#     # The reward received at each lane change action.
#     "lane_change_reward": 0.1, # (0)
#
#     "simulation_frequency": 15,  # (15) [Hz]
#     "policy_frequency": 1,  # (1) [Hz]
#
#     "normalize_reward": True, # (True)
#     "offroad_terminal": False, # (False)
#
#     # Changes for faster training
#     # cf. https://github.com/Farama-Foundation/HighwayEnv/issues/223
#     "disable_collision_checks": True,
# })

env.reset()


def display_script_help():
    print("Usage: python3 highway_agent.py train [model_id]")
    print("       python3 highway_agent.py test [model_id]")
    print()
    print("model_id: The name of the model to save/load (default: 'new')")

def get_paths():
    global save_base_path
    if len(sys.argv) > 2:
        model_id = sys.argv[2]
    else:
        model_id = 'new'

    save_path = os.path.join(save_base_path, model_id)
    model_path = os.path.join(save_path, "trained_model")

    return save_path, model_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        display_script_help()
        sys.exit(1)

    if sys.argv[1] == 'train':
        save_path, model_path = get_paths()


        # Settings adapted from
        # https://github.com/Farama-Foundation/HighwayEnv/blob/master/scripts/sb3_highway_dqn.py
        model = DQN('MlpPolicy', env,
                    policy_kwargs=dict(net_arch=[256, 256]),
                    learning_rate=5e-4,
                    buffer_size=15000,
                    learning_starts=200,
                    batch_size=32,
                    gamma=0.9,  # Discount factor
                    exploration_fraction=0.3,
                    exploration_initial_eps=1.0,
                    exploration_final_eps=0.05,
                    train_freq=1,
                    gradient_steps=1,
                    target_update_interval=50,
                    verbose=1,
                    tensorboard_log=save_path)


        # Save a checkpoint every 1000 steps
        checkpoint_callback = CheckpointCallback(
            save_freq=1000,
            save_path=save_path,
            name_prefix="rl_model"
        )

        model.learn(int(20_000), callback=checkpoint_callback, tb_log_name="new_dqn", progress_bar=True)
        model.save(model_path)


    elif sys.argv[1] == 'test':
        save_path, model_path = get_paths()

        model = DQN.load(model_path)
        env.configure({"simulation_frequency": 15})

        action_counter = [0]*5  # It seems model only takes one action; check this
        crashes = 0
        test_runs = 10

        ############## SAFETY CONTROLLER ##############
        safety_enforcer = Enforcer.Enforcer()
        safety_enforcer.upload_runtime_model()
        ###############################################

        for _ in range(test_runs):
            env.reset()
            road = env.road
            from highway_env.vehicle.kinematics import Vehicle

            # Define the position and lane for the new vehicle
            ego_vehicle = env.vehicle
            lane = road.network.get_closest_lane_index(ego_vehicle.position)
            position = [ego_vehicle.position[0] - 20, ego_vehicle.position[1]]  # 20m behind the ego
            new_vehicle = Vehicle(road, position, speed=20)  # Speed set to 20 m/s

            road.vehicles.append(new_vehicle)
            env.render()
            
            ############## SAFETY CONTROLLER ##############
            safety_enforcer.begin_enforcement()
            ###############################################

            state = env.reset()[0]
            done = False
            truncated = False
            while not done and not truncated:
                action = model.predict(state, deterministic=True)[0]

                ############## SAFETY CONTROLLER ##############
                action = safety_enforcer.sanitise_output(action)
                ###############################################

                next_state, reward, done, truncated, info = env.step(action)

                ############## SAFETY CONTROLLER ##############
                safety_enforcer.log_step_info(next_state, info)
                ###############################################

                state = next_state
                env.render()

                action_counter[action] += 1
                print('\rAction counter: ', action_counter, end='')  # Verify multiple actions are taken

                if info and info['crashed']:
                    crashes += 1
                    
            ############## SAFETY CONTROLLER ##############
            safety_enforcer.end_enforcement()
            ###############################################

        print("\rCrashes:", crashes, "/", test_runs, "runs", f"({crashes/test_runs*100:0.1f} %)")
        
        ############## SAFETY CONTROLLER ##############
        safety_enforcer.delete_runtime_model()
        ###############################################

        env.close()
    else:
        display_script_help()

    env.close()
