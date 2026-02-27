
# AICon (Agentic Intelligence for the Computing Continuum) 
### A simulator based developement framework of distributed management agents for the computing continuum

1) Installation

```bash
create conda environment with python 3.10
git clone --branch v1.0.1 https://github.com/ildefons/aicon.git
pip install ./requirements.txt
```

2) Examples

The ```examples\ayafs``` directory contain three examples with both a simulated setup and management network meant to control this simulated system. Other folders in ```examples``` contains uniquelly examples of simulated setups and we cannot guarantee the correct functionality due to heavy changes performed in the underlying simulator based on YAFS (see Acknowledgement below) and the same caution note applies to the ```tutorial_scenarios``` folder

```bash
export PYTHONPATH=$PYTHONPATH:~/YAFS/src/
cd examples/ayafs/SingleAgentAPL
python main.py
```

## References
 * Ildefons Magrans de Abril, Nefeli-Marina Rouska, Victor Casamayor, Schahram Dustdar, <A href="https://ieeexplore.ieee.org/document/11411901">iAICon: Agentic Intelligence for the Computing Continuum</A>, IEEE Internet Computing, Volume 29, Issue: 6, DOI: 10.1109/MIC.2025.3645964, Nov.-Dec.-2025.


## Acknowledgment

This framework builds upon [YAFS (Yet Another Fog Simulator)](https://github.com/acsicuib/YAFS). We acknowledge and thank the YAFS authors for their foundational work in fog computing simulation, which our project extends to support the study and development of distributed management agents for continuum computing systems.

