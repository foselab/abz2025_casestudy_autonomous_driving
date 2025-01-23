import pandas as pd
import numpy as np
from highway_env.utils import lmap  # Linear mapping function for normalization/denormalization

import logging_manager

logger = logging_manager.get_logger(__name__)
np.set_printoptions(precision=2, suppress=True)

y_to_lane_map = {
    0.0: "LEFT",
    4.0: "MIDDLE",
    8.0: "RIGHT"
}
lane_to_y_map = {value: key for key, value in y_to_lane_map.items()}

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
        if 0 < x < x_front:
            x_front, vx_front = x, vx
    return x_front, vx_front

def _extract_self(observation):
    """
    Extract x position and velocity of the ego vehicle (i.e. the controlled vehicle, self)
    """
    return observation[0][1], observation[0][3] 

def _extract_self_lane(observation):
    """
    Extract the lane of the ego vehicle (i.e. the controlled vehicle, self)
    """
    y = observation[0][2]
    vy = observation[0][4]
    if y in y_to_lane_map and vy == 0: #double check that the vehicle is not changing lane
        return y_to_lane_map[y]
    return None

def _extract_front_from_lane(observation, lane):
    """
    Extract the x position and x velocity of the nearest front vehicle in the specified lane.

    A vehicle that has started to enter or leave the lane is considered to be in the lane.
    """
    x_front = float('inf')
    vx_front = None
    for row in observation[1:]:
        x = row[1]
        y = row[2]
        vx = row[3]
        in_lane =  (
            (lane == "LEFT" and y < lane_to_y_map["MIDDLE"]) or
            (lane == "MIDDLE" and lane_to_y_map["LEFT"] < y < lane_to_y_map["RIGHT"]) or
            (lane == "RIGHT" and y > lane_to_y_map["MIDDLE"])
        )
        if 0 < x < x_front and in_lane:
            x_front, vx_front = x, vx
    return x_front, vx_front

def _process_multi_lane(observation):
    """
    Extract the position and speed information of the controlled vehicle
    and of nearest (on the x) vehicles one each lane
    """
    x_self, vx_self = _extract_self(observation)
    x_lane = _extract_self_lane(observation)
    if (x_lane == None):
        return float(x_self), float(vx_self), 0, 0
    x_left, vx_left = _extract_front_from_lane(observation, "LEFT")
    x_middle, vx_middle = _extract_front_from_lane(observation, "MIDDLE")
    x_right, vx_right = _extract_front_from_lane(observation, "RIGHT")
    logger.info(f"Ego vehicle x ({x_lane}): {x_self:.2f}, vx: {vx_self:.2f}")
    logger.info(f"LEFT lane vehicle x: {x_left:.2f}, vx: {vx_left:.2f}")
    logger.info(f"MIDDLE lane vehicle x: {x_middle:.2f}, vx: {vx_middle:.2f}")
    logger.info(f"RIGHT lane vehicle x: {x_right:.2f}, vx: {vx_right:.2f}")
    if x_middle == float('inf'):
        return float(x_self), float(vx_self), x_middle, vx_middle
    return float(x_self), float(vx_self), float(x_middle), float(vx_middle)

def _process_single_lane(observation):
    """
    Extract the position and speed information of the controlled vehicle and its front vehicle
    """
    x_self, v_self = _extract_self(observation)
    x_front, v_front = _extract_front(observation)
    logger.info(f"Ego vehicle x: {x_self:.2f}, vx: {v_self:.2f}")
    if x_front == float('inf'):
        logger.info("Front vehicle: not observable")
        return float(x_self), float(v_self), x_front, v_front
    logger.info(f"Front vehicle x: {x_front:.2f}, vx: {v_front:.2f}")
    return float(x_self), float(v_self), float(x_front), float(v_front)
    
    
def process(env, observation):
    """
    Process the observations, denormalise and extract the position and speed information of the vehicles
    """
    d_a_observation = _denormalize_observation(env.observation_type, observation)
    logger.info(f"Observation:\n {observation}")
    logger.info(f"De-normalized Absolute Observations:\n {d_a_observation}")
    if env.config["lanes_count"] == 3:
        return _process_single_lane(d_a_observation) #_process_multi_lane(d_a_observation)
    return _process_single_lane(d_a_observation)