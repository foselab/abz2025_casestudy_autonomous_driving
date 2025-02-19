# ABZ 2025 Case Study - replication Package for: Safety enforcement for autonomous driving on a simulated highway using Asmeta models&#8203;@run.time

This repository contains the replication package for the paper Safety enforcement for autonomous driving on a simulated highway using Asmeta models&#8203;@run.time for the Case Study [Safety Controller for Autonomous Driving](https://abz-conf.org/case-study/abz25/) of [ABZ conference 2025](https://abz-conf.org/2025/).
The replication package includes the Python software artifacts for the enforcement framework, the Asmeta models, and data leading us to our findings.

## Initial setup

This guide assumes you are using a **Linux environment** (e.g. Windosw Subsystem for Linux WSL) with **Python 3.11** installed. \
It is possible to install Python 3.11 along with its package manager and virtual environment support by executing the following commands:

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update && sudo apt upgrade
sudo apt install -y python3.11 python3-pip python3.11-venv
```

Once Python is ready, move to your working dir and execute these commands:

```bash
git clone https://github.com/foselab/abz2025_casestudy_autonomous_driving
cd abz2025_casestudy_autonomous_driving/
python3.11 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Running tests using the Enforcement Framework

### Start the `Asmeta@run.time` server on port 8080
In order to run the server it is necessary to have Java JRE 17 or higher and Python installed on the machine. \
For example, in Linux environments, you can install Java with the command:
```bash
sudo apt install default-jre
```

To run the server, move to the `asmeta server` folder and run:

```bash
python asmeta_runtime_server.py
```

### Execute the tests on the autonomous driving system.
Once the server is up, move to the repository's base folder and run:

```bash
source env/bin/activate
cd enforcement
# To run without enforcement (the server is NOT required):
python autonomous_driving_system.py
# To run with enforcement (the server is required):
python autonomous_driving_system.py run_enforcer
```

Whether running with or without enforcement, the configuration of the environment, the controlled vehicle, and other simulation-related parameters can be modified by editing the `enforcement/config.json` file.

The following is a brief description of each field in the configuration file:
* **single_lane**: if `true`, run the simulations on a highway with a single lane; if `false`, use a highway with 3 lanes.
* **adversarial**: if `true`, use the adversarial AI agent; if `false`, use the base (non-adversarial) AI agent.
* **simulation**:
  * **test_runs**: the number of test runs to be executed.
  * **simulation_frequency**: the simulation frequency (i.e., the simulation frames in a simulation second), expressed in Hz.
  * **policy_frequency**: the policy frequency (i.e., the number of decisions taken by the controlled vehicle during a simulation second), expressed in Hz.
  * **duration**: the duration of each test run, expressed in simulation seconds.
* **enforcer**:
  * **ip**: the IP address of the `Asmeta@run.time` server.
  * **base_port**: the port on which the `Asmeta@run.time` server listens (e.g., 8080).
  * **spec_path**: the path to the folder containing the Asmeta models (you can use `"../asmeta spec/models"`).
  * **runtime_model**: the Asmeta model to be used at runtime.
* **logging**:
  * **level**: the logging level.
  * **target_folder**: the directory where log file is stored.
* **experiments**:
  * **write_to_xlsx**: if `true`, collect and write experimental data to Excel file.
  * **target_folder**: the directory where experimental data is stored, ignored if **write_to_xlsx** is set to `false`.

**NOTE**
* **the `"policy_frequency"` nested-field should be set to `1`, otherwise it is necessary to modify the ASMETA spec (specified in the `"runtime_model"` nested-field) accordingly (i.e., initializing the `resp_time` controlled function to the inverse of the policy frequency).**
* **the `"ip"` nested-field is optional and if it is not set the ip is dinamically determined (especially if the script is running in Windosw Subsystem for Linux WSL, otherwise, it is set to `localhost`).**

For example, assuming a local server is running the `AsmetaS@run.time` simulator on `localhost:8080`, the following configuration sets up 1 test run lasting 100 simulation seconds in a multi-lane scenario with an adversarial agent and the `SafetyEnforcerKeepRight.asm` as runtime model:

```json
{
  "single_lane": false,
  "adversarial": true,
  "simulation": {
    "test_runs": 1,
    "simulation_frequency": 15,
    "policy_frequency": 1,
    "duration": 100},
  "enforcer":{
    "ip": "localhost",
    "base_port": 8080,
    "spec_path": "../asmeta spec/models",
    "runtime_model": "SafetyEnforcerKeepRight.asm"},
  "logging":{
    "level": "INFO",
    "target_folder": "log"},
  "experiments": {
    "write_to_xlsx": false,
    "target_folder": "data/temp"
  }
}
```
