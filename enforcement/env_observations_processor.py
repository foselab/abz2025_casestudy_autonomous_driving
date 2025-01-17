import pandas as pd
import numpy as np
from highway_env.utils import lmap  # Linear mapping function for normalization/denormalization

import logging_manager

logger = logging_manager.get_logger(__name__)

def _denormalize_observation(obs_config, normalized_observation):
    """
    Denormalize the input observation and make it absolute
    """
    features = obs_config.features
    features_range = obs_config.features_range
    df = pd.DataFrame(normalized_observation, columns=features)
    # Denormalize each feature
    for feature, f_range in features_range.items():
        if feature in df:
            df[feature] = lmap(df[feature], [-1, 1], [f_range[0], f_range[1]])
    # Make not controlled vehicles rows absolute
    for col in features:
        if col != "presence":
            df.iloc[1:, df.columns.get_loc(col)] += df.iloc[0, df.columns.get_loc(col)]
    return df.values

def _extract_front(observation):
    """
    Extract x position and velocity of the vehicles behind and in front of the ego vehicle
    """
    x_front = float('inf')
    vx_front = None
    for row in observation[1:]:
        x = row[1]
        vx = row[3]
        if x > 0 and x < x_front:
            x_front, vx_front = x, vx
    return x_front, vx_front 

def _extract_self(observation):
    return observation[0][1], observation[0][3] 

def log_step_info(obs_config, next_state, reward, info):
    """
    Log info about a step on the environment.
    """
    observation = _denormalize_observation(obs_config, next_state)
    x_rear, vx_rear, x_front, vx_front = _extract_rear_and_front(observation)
    x_ego, vx_ego = _extract_ego(observation)
    if x_rear == float('-inf'):
        x_rear = vx_rear = "N/A"
    if x_front == float('inf'):
        x_front = vx_front = "N/A"
    speed = info.get("speed", "N/A")
    crashed = info.get("crashed", "N/A")
    rewards = info.get("rewards", "N/A")
    logger.info("Observation:\n %s", next_state)
    logger.info("De-normalized Absolute Observations:\n %s", observation)
    logger.info("Ego vehicle information:")
    logger.info("*Ego vehicle x: %s, vx: %s", x_ego, vx_ego)
    logger.info("*Speed: %s", speed)
    logger.info("*Crashed: %s", crashed)
    logger.info("*Reward: %s", reward)
    logger.info("*Rewards: %s", rewards)
    logger.info("Other vehicles information:")
    logger.info("*Rear (NOT EGO) vehicle x: %s, vx: %s", x_rear, vx_rear)
    logger.info("*Front vehicle x: %s, vx: %s", x_front, vx_front)

def process(obs_config, observation):
    observation = _denormalize_observation(obs_config, observation)
    x_front, v_front = _extract_front(observation)
    x_self, v_self = _extract_self(observation)
    return float(x_self), float(v_self), float(x_front), float(v_front)