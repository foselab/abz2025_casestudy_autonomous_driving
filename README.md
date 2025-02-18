# ABZ 2025 Case Study - replication Package for: `Safety enforcement for autonomous driving on a simulated highway using Asmeta models@run.time`

This repository contains the replication package for the paper `Safety enforcement for autonomous driving on a simulated highway using Asmeta models@run.time` for the Case Study [Safety Controller for Autonomous Driving](https://abz-conf.org/case-study/abz25/) of [ABZ conference 2025](https://abz-conf.org/2025/).
The replication package includes the Python software artifacts for the enforcement framework, the Asmeta models, and data leading us to our findings.

## Initial setup

This guide assumes you are using a **Linux environment** with **Python 3.11**. \
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
Move to the `asmeta server` folder and run:

```bash
python asmeta_runtime_server.py
```

**Note that it is not mandatory to execute the server on Linux.**

### Execute the tests on the autonomous driving system.
Move to the repository's base folder and run:

```bash
source env/bin/activate
cd enforcement
# To run without enforcement:
python autonomous_driving_system.py
# To run with enforcement:
python autonomous_driving_system.py run_enforcer
```

Whether running with or without enforcement, the configuration of the environment, the controlled vehicle, and other simulation-related parameters can be modified by editing the `enforcement/config.json` file.

For example, assuming a local server is running the `AsmetaS@run.time` simulator on `localhost:8080`, the following configuration sets up 1 test run lasting 100 simulation seconds in a multi-lane scenario with an adversarial agent and the `SafetyEnforcerKeepRight.asm` as runtime model:

```json
{
  "single_lane": false,
  "adversarial": true,
  "simulation": {
    "test_runs": 1,
    "simulation_frequency": 15,
    "policy_frequency": 1,
    "duration": 50},
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
**Note that the `"ip` nested-field is optional and if it is not set the ip is dinamically determined (especially if the script is running in Windosw Subsystem for Linux WSL, otherwise, it is set to `localhost`).**
