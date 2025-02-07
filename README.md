# ABZ 2025 Case Study

## Training and testing of agents

Setup:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

The agent for the Highway Environment can be trained or tested via command line:

```bash
# To train a new model (save under models/highway_env):
python highway_agent.py train


# Loads the trained model and runs and renders episodes over its behaviour:
python highway_agent.py test
```

## Running tests using the Enforcement Framework
This guide assumes you are using a **Linux environment** with **Python 3.11**. \
Setup:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Tests on the autonomous driving system can be run either with or without enforcement via the command line:

```bash
cd enforcement

# To run without enforcement:
python autonomous_driving_system.py


# To run with enforcement:
python autonomous_driving_system.py run_enforcer
```

In both cases, the configuration of the environment, the controlled vehicle, and other simulation-related parameters can be modified by editing the `enforcement/config.json` file. \
For example, assuming a local server is running the AsmetaS@run.time simulator on port 8080, the following configuration sets up 10 test runs, each lasting 100 simulation seconds, in a multi-lane scenario with an adversarial agent and the `SafetyEnforcerKeepRight.asm` as runtime model:

```json
{
  "single_lane": false,
  "adversarial": true,
  "simulation": {
    "test_runs": 10,
    "simulation_frequency": 15,
    "policy_frequency": 1,
    "duration": 100},
  "enforcer":{
    "base_port": 8080,
    "spec_path": "../asmeta spec/models",
    "runtime_model": "SafetyEnforcerKeepRight.asm"},
  "logging":{
    "level": "INFO",
    "target_folder": "log"},
  "experiments": {
    "write_to_xlsx": true,
    "folder": "data/"
  }
}
```

## Scenarios


In the following, we provide some scenarios for a single-agent controller.
The controlled vehicle (ego vehicle) is marked in red.
Rosa vehicles are vehicles in the same lane for which the safety distance is relevant.
Purple vehicles are vehicles for which the distance will become relevant when switching lanes.
Blue vehicles are vehicles for which the safety distance will not be relevant in the next cycle.


## Scenario 1


| <img src="images/Scenario1_1.png" alt="Scenario 1.1" width="150%">                         | <img src="images/Scenario1_2.png" alt="Scenario 1.2" width="150%"> | <img src="images/Scenario1_3.png" alt="Scenario 1.3" width="150%"> |
|--------------------------------------------------------------------------------------------|--------------------------------------------------------------------|--------------------------------------------------------------------|
| A vehicle approaches another vehicle in the same lane from behind, the distance decreases. | The Ego vehicle brakes.                                            |The Ego vehicle continues braking to maintain the safety distance. |


## Scenario 2


 ![Scenario 2](images/Scenario2_1.png)                                                      | ![Scenario 2](images/Scenario2_2.png)        | ![Scenario 2](images/Scenario2_3.png)                                    
|--------------------------------------------------------------------------------------------|----------------------------------------------|--------------------------------------------------------------------------|
| A vehicle approaches another vehicle in the same lane from behind, the distance decreases. | The Ego vehicle switches to the right lane.  | The Ego vehicle completes switching to the right lane and accelerates.   |


## Scenario 3

 ![Scenario 3](images/Scenario3_1.png)                   | ![Scenario 3](images/Scenario3_2.png)                                              | ![Scenario 3](images/Scenario3_3.png)       
|---------------------------------------------------------|------------------------------------------------------------------------------------|---------------------------------------------|
| There is another vehicle on another lane further right. | The Ego vehicle switches to the right lane, as the safety distance is maintained.  | The Ego  vehicle continues driving forward. |


## Scenario 4

![Scenario 4](images/Scenario4_1.png)                   | ![Scenario 4](images/Scenario4_2.png)                                                       | ![Scenario 4](images/Scenario4_3.png)
|---------------------------------------------------------|---------------------------------------------------------------------------------------------|---------------------------------------------|
| There is another vehicle on another lane further right. | The Ego vehicle cannot switch to the center lane, as the safety distance is not maintained. | The Ego vehicle continues driving forward.  |


## Scenario 5

 ![Scenario 5](images/Scenario5_1.png)         | ![Scenario 5](images/Scenario5_2.png)           | ![Scenario 5](images/Scenario5_3.png)                                                 
|-----------------------------------------------|-------------------------------------------------|---------------------------------------------------------------------------------------|
| The Ego Vehicle drives on the left-most lane. | There is another vehicle on the right-most lane | Both vehicles decide to switch to the center lane, while maintaining safety distances |
