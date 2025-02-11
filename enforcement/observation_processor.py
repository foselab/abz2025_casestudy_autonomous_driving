import math
import pandas as pd
import numpy as np
from highway_env.utils import lmap  # Linear mapping function for normalization/denormalization

import logging_manager

class ObservationProcessor:

    # A vehicle is said to be on a lane and not leaving or entering it 
    # if its y-position is equal to the y-coordinate associated with the lane +/- the tolerance.  
    Y_TOLERANCE = 0.1

    def __init__(self, env, observation):
        """
        Initialize the class, denormalize the input observation and make it absolute
        """
        self.logger = logging_manager.get_logger(__name__)
        np.set_printoptions(precision=2, suppress=True)

        self.y_to_lane_map = {
            0.0: "LEFT",
            4.0: "MIDDLE",
            8.0: "RIGHT"
        }
        self.lane_to_y_map = {value: key for key, value in self.y_to_lane_map.items()}

        self.env = env

        self.d_a_observation = self._denormalize_observation(self.env.observation_type, observation)
        self.logger.info(f"Observation:\n {observation}")
        self.logger.info(f"De-normalized Absolute Observations:\n {self.d_a_observation}")

    def _denormalize_observation(self, obs_config, normalized_observation):
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

    def _is_on_lane(self, y, lane, tolerance=Y_TOLERANCE):
        """
        Given the y position of a vehicle and a lane, return true if the vehicle is occupying the lane.

        A vehicle is occupying a lane if:
            o	is traveling straight ahead in the lane
            o	is leaving the lane but not yet travelling straight on the other lane
            o	is another lane to enter the lane in question and not yet travelling straight on the lane in question
        
        Assumption: a vehicle il proceeding straight on a lane if its y position is close enough to the y position associated to that lane.
        """
        if lane == "LEFT":
            return (
                y < self.lane_to_y_map["MIDDLE"] and
                not math.isclose(y, self.lane_to_y_map["MIDDLE"], abs_tol = tolerance)
            )
        elif lane == "MIDDLE":
            return (
                self.lane_to_y_map["LEFT"] < y < self.lane_to_y_map["RIGHT"] and
                not math.isclose(y, self.lane_to_y_map["LEFT"], abs_tol = tolerance) and
                not math.isclose(y, self.lane_to_y_map["RIGHT"], abs_tol = tolerance)
            )
        elif lane == "RIGHT":
            return (
                y > self.lane_to_y_map["MIDDLE"] and
                not math.isclose(y, self.lane_to_y_map["MIDDLE"], abs_tol = tolerance)
            )
        raise Exception(f"{lane} should be 'LEFT', 'RIGHT' or 'MIDDLE'")

    def _extract_self_lane(self):
        """
        Extract the lane of the ego vehicle (i.e. the controlled vehicle, self), None if it is changing lane

        A vehicle is said to be on a lane and not leaving or entering it 
        if its y-position is equal to the y-coordinate associated with the lane +/- the tolerance.
        """
        y = self.d_a_observation[0][2]
        return next((self.y_to_lane_map[lane_y_pos] for lane_y_pos in self.y_to_lane_map if math.isclose(y, lane_y_pos, abs_tol=self.Y_TOLERANCE)), None)
    
    def _extract_self(self):
        """
        Extract x position and velocity of the ego vehicle (i.e. the controlled vehicle, self)
        """
        return self.d_a_observation[0][1], self.d_a_observation[0][3] 

    def _extract_front_single_lane(self):
        """
        Extract x position and velocity of the vehicle in front of the ego vehicle for single lane scenario
        """
        x_front = float('inf')
        vx_front = None
        for row in self.d_a_observation[1:]:
            presence = row[0]
            x = row[1]
            vx = row[3]
            if presence == 1 and 0 <= x < x_front:
                x_front, vx_front = x, vx
        return x_front, vx_front

    def _extract_front_from_lane(self, lane):
        """
        Extract the x position and x velocity of the nearest front vehicle in the specified lane.

        A vehicle that has started to enter or leave the lane is considered to be in the lane until it completes the maneuver.
        """
        x_front = float('inf')
        vx_front = None
        for row in self.d_a_observation[1:]:
            presence = row[0]
            x = row[1]
            y = row[2]
            vx = row[3]
            if presence == 1 and 0 < x < x_front and self._is_on_lane(y, lane):
                x_front, vx_front = x, vx
        return x_front, vx_front

    def _process_multi_lane(self):
        """
        Extract the position and speed information of the controlled vehicle
        and its front vehicle and whether the right lane is free or not for a multi lane highway

        Assumption: the controlled vehicle is not changing lane

        Safety policy:
        When considering which vehicles are occupying a lane, the following vehicles are considered:
            o	All the vehicles traveling straight ahead in the lane
            o	All the vehicles leaving the lane but not yet travelling straight on the other lane
            o	All the vehicles leaving another lane to enter the lane in question and not yet travelling straight on the lane in question
        """
        x_self, vx_self = self._extract_self()
        x_lane = self._extract_self_lane()
        x_front, vx_front = self._extract_front_from_lane(x_lane)
        if x_lane == "RIGHT":
            right_lane_free = False
        else:
            right_lane = "MIDDLE" if x_lane == "LEFT" else "RIGHT"
            x_right, _ = self._extract_front_from_lane(right_lane)
            right_lane_free = (x_right == float("inf"))
        return x_self, vx_self, x_front, vx_front, right_lane_free    

    def _process_single_lane(self):
        """
        Extract the position and speed information of the controlled vehicle and its front vehicle
        for a single lane highway 
        """
        x_self, v_self = self._extract_self()
        x_front, v_front = self._extract_front_single_lane()
        return x_self, v_self, x_front, v_front
        
    def process(self):
        """
        Process the observations, denormalise and extract the position and speed of the controlled vehicle and its front vehicle
        and whether the right lane is free or not

        Assumption: the controlled vehicle is not changing lane
        """
        assert not self.is_controlled_vehicle_changing_lane()

        if self.env.config["lanes_count"] == 3:
            x_self, v_self, x_front, v_front, right_lane_free = self._process_multi_lane()
        else:
            right_lane_free = False # in single lane, the right lane is not free because it does not exist
            x_self, v_self, x_front, v_front = self._process_single_lane()
        
        self.logger.info(f"Ego vehicle x: {x_self:.2f}m, vx: {v_self:.2f}m/s")
        if x_front == float('inf'):
            self.logger.info("Front vehicle: not observable")
        else:
            self.logger.info(f"Front vehicle x: {x_front:.2f}m, vx: {v_front:.2f}m/s")
        self.logger.info(f"Right lane free: {right_lane_free}")

        x_self, v_self, x_front = map(float, (x_self, v_self, x_front))
        if v_front != None:
            v_front = float(v_front)

        return x_self, v_self, x_front, v_front, right_lane_free

    def is_controlled_vehicle_changing_lane(self):
        """
        Return true if the contorlled vehicle is changing lane, i.e. if
        its y-position is NOT equal to the y-coordinate associated with ANY lane (considering the tolerance).  
        """
        return self._extract_self_lane() == None
    
    def is_controlled_vehicle_on_right_lane(self):
        """
        Return true if the contorlled vehicle is on the right lane i.e. if
        its y-position is equal to the y-coordinate associated with the right lane (considering the tolerance).

        In single lane scenario, always return true
        """
        return self.env.config["lanes_count"] == 1 or self._extract_self_lane() == "RIGHT"
        