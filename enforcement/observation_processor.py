import pandas as pd
import numpy as np
from highway_env.utils import lmap  # Linear mapping function for normalization/denormalization

import logging_manager

logger = logging_manager.get_logger(__name__)
np.set_printoptions(precision=2, suppress=True)

def _denormalize_observation(obs_config, normalized_observation):
    """
    Denormalize the input observation and make it absolute
    """
    features = obs_config.features
    features_range = obs_config.features_range
    df = pd.DataFrame(normalized_observation, columns=features)
    # Denormalize each feature
    for feature, f_range in features_range.items():
        df[feature] = lmap(df[feature], [-1, 1], [f_range[0], f_range[1]])
    # Make rows of not controlled vehicles absolute
    for feature in features:
        if feature != "presence":
            df.iloc[1:, df.columns.get_loc(feature)] += df.iloc[0, df.columns.get_loc(feature)]
    # If presence is 0, all the features should be 0
    for index in range(1, len(df)):
        if df.iloc[index, 0] == 0:
            df.iloc[index, 1:] = 0
    return df.values

def _extract_front(observation):
    """
    Extract x position and velocity of the vehicle in front of the ego vehicle
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
    """
    Extract x position and velocity of the ego vehicle (i.e. the controlled vehicle, self)
    """
    return observation[0][1], observation[0][3] 

def process(obs_config, observation):
    """
    Process the observations, denormalise and extract the position and speed information of the ego vehicle and the vehicle in front
    """
    d_a_observation = _denormalize_observation(obs_config, observation)
    x_front, v_front = _extract_front(d_a_observation)
    x_self, v_self = _extract_self(d_a_observation)
    logger.info("Observation:\n %s", observation)
    logger.info("De-normalized Absolute Observations:\n %s", d_a_observation)
    logger.info("Ego vehicle x: %s, vx: %s", x_self, v_self)
    if x_front == float('inf'):
        logger.info("Front vehicle: not observable")
        return float(x_self), float(v_self), x_front, v_front
    logger.info("Front vehicle x: %s, vx: %s", x_front, v_front)
    return float(x_self), float(v_self), float(x_front), float(v_front)