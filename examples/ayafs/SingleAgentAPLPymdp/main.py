"""
    Scenario: Single management Agent doing an Action-perception loop using active inferene package Pymdp

    @author: Ildefons Magrans de Abril
"""

import random
import networkx as nx
import argparse
from pathlib import Path
import time
import numpy as np

from yafs.core import Sim
from yafs.application import Application,Message,LinearQoS

from yafs.population import *
from yafs.topology import Topology

from yafs.stats import Stats
from yafs.distribution import deterministic_distribution
from yafs.application import fractional_selectivity

from yafs.placement import Placement
from yafs.selection import Selection

# ILDE: added as part of the new agent management network 
from yafs.management_network import ManagementAgent, ManagementAgentNetwork, DiscreteNodeIPTInterventions
import numpy as np

from pymdp.agent import Agent
from pymdp.maths import softmax
from pymdp import utils

# Custom agent classes
class CloudAgent(ManagementAgent):
    def __custom_init__(self):
        self.state_id = 0

        #Initialize pymdp agent A,B,C,D 

        n_f1 = len(self.actions['discrete_node_ipt'].iptl)
        n_f2 = len(self.metrics["node_average_waiting_time"].post.bins)
        self.state_factors = [n_f1, n_f2]
        self.n_state_factors = [n_f1, n_f2]

        self.obs_modalities = [n_f1, n_f2] # same observation as hidden states
        self.n_obs_modalities = [n_f1, n_f2]

        self.ACTIONS = list(range(len(self.actions['discrete_node_ipt'].iptl))) 
        self.n_actions = len(self.ACTIONS)

        # ---from pymdp import utils----------------------
        # Dirichlet priors (pseudo-counts)
        # -------------------------
        self.alpha_A = 1.0   # prior for A counts
        self.alpha_B = 1.0   # prior for B counts

        # ---------- Build A_dir ----------
        # Each A[m] has shape (obs_dim_m, s1, s2, ..., sF)
        self.A_dir = utils.obj_array( len(self.n_obs_modalities) )
        for m, n_o in enumerate(self.n_obs_modalities):
            shape = [n_o] + list(self.n_state_factors)
            self.A_dir[m] = np.ones(shape) * self.alpha_A

        # ---------- Build B_dir  ----------
        # B_f of shape (s_f_next, s_f, n_actions) for every factor.
        self.B_dir = utils.obj_array( len(self.n_state_factors) )
        for m, n_f in enumerate(self.n_state_factors):
            self.B_dir[m] = np.ones((n_f, n_f, self.n_actions)) * self.alpha_B

        # -------------------------
        # Preferences (C) and initial state priors (D)
        # -------------------------
        # Very weak/flat preferences initially (agent indifferent)

        self.C = utils.obj_array(len(self.n_obs_modalities))
        for m, n_o in enumerate(self.n_obs_modalities):
            self.C[m] = np.ones(n_o) / n_o        

        self.D = utils.obj_array(len(self.n_state_factors))
        for m, n_s in enumerate(self.n_obs_modalities):
            self.D[m] = np.ones(n_s) / n_s  

        # -------------------------
        # Build initial normalized A & B to pass to Agent
        # -------------------------
        def normalize_A_from_dir(A_dir):
            """Normalize each A_dir into probability A matrices expected by pymdp."""
            A_norm = utils.obj_array(len(A_dir))
            for m in range(len(A_dir)):
                a_dir = A_dir[m]
                # normalize over the observation axis' columns: each column (given state combination) sums to 1
                # axis=0 is obs axis; keepdims so broadcasting works
                A_norm[m] = a_dir / a_dir.sum(axis=0, keepdims=True)
            return A_norm

        def normalize_B_from_dir(B_dir):
            """Normalize each B_dir into probability B matrices expected by pymdp."""
            B_norm = utils.obj_array(len(B_dir))
            for m in range(len(B_dir)):
                # For each action, normalize columns (current state) so B[:, s, a] sums to 1
                b_dir = B_dir[m]
                for a in range(b_dir.shape[2]):
                    cols = b_dir[:, :, a]
                    # normalize each column
                    col_sums = cols.sum(axis=0, keepdims=True)  # shape (1, n_s)
                    # avoid divide-by-zero
                    col_sums[col_sums == 0] = 1.0
                    b_dir[:, :, a] = cols / col_sums
                B_norm[m] = b_dir
            return B_norm

        self.A_init = normalize_A_from_dir(self.A_dir)
        self.B_init = normalize_B_from_dir(self.B_dir)
        
        # -------------------------
        # Create pymdp Agent with learning enabled
        # -------------------------
        self.pymdp_agent = Agent(
                    A=self.A_init,
                    B=self.B_init,
                    C=self.C,
                    D=self.D,
                    policy_len=1        # planning horizon (tweak as you like)
                    )

        print(1)
         


    def agent_behavior(self, collected_metrics):
        """Retrieve and log incoming messages to cloud (node_id)."""

        wt = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == self.node_id][0]['value']
        ipt = [item for item in collected_metrics if item['metric'] == 'NodeIPT' and item['node_id'] == self.node_id][0]['value']

        print("wt:",wt, ", ipt:",ipt)

        myactions2 = self.actions['discrete_node_ipt']
        
        if self.sim.env.now >= 2000 and wt >= 4:
            myactions2(action_id=1, node_id=self.node_id)
        elif self.sim.env.now >= 4000: 
            if wt == 1:
                myactions2(action_id=0, node_id=self.node_id)
            elif wt>=4:
                myactions2(action_id=1, node_id=self.node_id)       



class SensorAgent(ManagementAgent):
    def agent_behavior(self, collected_metrics):
        """Sensor monitors metrics (no actions for now)."""

        #print("SensorAgent.get_management_action()")

        return []  # Extensible for future logic

class ActuatorAgent(ManagementAgent):
    def agent_behavior(self, collected_metrics):
        """Actuator monitors metrics (no actions for now)."""

        #print("ActuatorAgent.get_management_action()")

        return []  # Extensible for future logic

class MinimunPath(Selection):

    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):

        """
        Computes the minimun path among the source elemento of the topology and the localizations of the module

        Return the path and the identifier of the module deployed in the last element of that path
        """
        node_src = topology_src
        DES_dst = alloc_module[app_name][message.dst]

        # print(("GET PATH"))
        # print(("\tNode _ src (id_topology): %i" %node_src))
        # print(("\tRequest service: %s " %message.dst))
        # print(("\tProcess serving that service: %s " %DES_dst))

        bestPath = []
        bestDES = []

        for des in DES_dst: ## In this case, there are only one deployment
            dst_node = alloc_DES[des]
            #print(("\t\t Looking the path to id_node: %i" %dst_node))

            path = list(nx.shortest_path(sim.topology.G, source=node_src, target=dst_node))

            bestPath = [path]
            bestDES = [des]

        return bestPath, bestDES



class MinPath_RoundRobin(Selection):

    def __init__(self):
        self.rr = {} #for a each type of service, we have a mod-counter

    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):
        """
        Computes the minimun path among the source elemento of the topology and the localizations of the module

        Return the path and the identifier of the module deployed in the last element of that path
        """
        node_src = topology_src
        DES_dst = alloc_module[app_name][message.dst] #returns an array with all DES process serving


        if message.dst not in self.rr.keys():
            self.rr[message.dst] = 0


        print(("GET PATH"))
        print(("\tNode _ src (id_topology): %i" %node_src))
        print(("\tRequest service: %s " %(message.dst)))
        print(("\tProcess serving that service: %s (pos ID: %i)" %(DES_dst,self.rr[message.dst])))

        bestPath = []
        bestDES = []

        for ix,des in enumerate(DES_dst):
            if message.name == "M.A":
                if self.rr[message.dst]==ix:
                    dst_node = alloc_DES[des]

                    path = list(nx.shortest_path(sim.topology.G, source=node_src, target=dst_node))

                    bestPath = [path]
                    bestDES = [des]

                    self.rr[message.dst] = (self.rr[message.dst]+ 1) % len(DES_dst)
                    break
            else: #message.name == "M.B"

                dst_node = alloc_DES[des]

                path = list(nx.shortest_path(sim.topology.G, source=node_src, target=dst_node))
                if message.broadcasting:
                    bestPath.append(path)
                    bestDES.append(des)
                else:
                    bestPath = [path]
                    bestDES = [des]

        return bestPath, bestDES


class CloudPlacement(Placement):
    """
    This implementation locates the services of the application 
    in the cheapest cloud regardless of where the sources or sinks are located.

    It only runs once, in the initialization.

    """
    def initial_allocation(self, sim, app_name):
        #We find the ID-nodo/resource
        value = {"mytag": "cloud"} # or whatever tag

        id_cluster = sim.topology.find_IDs(value)
        app = sim.apps[app_name]
        services = app.services

        for module in services:
            if module in self.scaleServices:
                for rep in range(0, self.scaleServices[module]):
                    idDES = sim.deploy_module(app_name,module,services[module],id_cluster)

    #end function

RANDOM_SEED = 1

def create_application():
    # APLICATION
    a = Application(name="SimpleCase")

    # (Camera) --> (ServiceA) --> (dashboard)
    a.set_modules([{"Camera":{"Type":Application.TYPE_SOURCE}},
                   {"ServiceA": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"Dashboard": {"Type": Application.TYPE_SINK}}
                  ])
    """
    Messages among MODULES (AppEdge in iFogSim)
    """
    
    m_a = Message("M.A", "Camera", "ServiceA", instructions=20*10**6, bytes=1000, qos=LinearQoS(L=0.05,R=1.0))   
    # ILDE: I have added new attribute qos so I can monitor and control the QoS of this message
    m_b = Message("M.B", "ServiceA", "Dashboard", instructions=30*10**6, bytes=500)

    """
    Defining which messages will be dynamically generated # the generation is controlled by Population algorithm
    """
    a.add_source_messages(m_a)

    """
    MODULES/SERVICES: Definition of Generators and Consumers (AppEdges and TupleMappings in iFogSim)
    """
    # MODULE SERVICES
    a.add_service_module("ServiceA", m_a, m_b, fractional_selectivity, threshold=1.0)

    return a


def create_json_topology():
    """
       TOPOLOGY DEFINITION

       Some attributes of fog entities (nodes) are approximate
       """

    ## MANDATORY FIELDS
    topology_json = {}
    topology_json["entity"] = []
    topology_json["link"] = []

    cloud_dev    = {"id": 0, "model": "cloud","mytag":"cloud", "IPT": 300 * 10 ** 5, "RAM": 40000,"COST": 3,"WATT":20.0}
    sensor_dev   = {"id": 1, "model": "sensor-device", "IPT": 100* 10 ** 6, "RAM": 4000,"COST": 3,"WATT":40.0}
    actuator_dev = {"id": 2, "model": "actuator-device", "IPT": 100 * 10 ** 7, "RAM": 4000,"COST": 3, "WATT": 40.0}

    link1 = {"s": 0, "d": 1, "BW": 1, "PR": 1}
    link2 = {"s": 0, "d": 2, "BW": 1, "PR": 1}

    topology_json["entity"].append(cloud_dev)
    topology_json["entity"].append(sensor_dev)
    topology_json["entity"].append(actuator_dev)
    topology_json["link"].append(link1)
    topology_json["link"].append(link2)

    return topology_json

def main(simulated_time):

    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    folder_results = Path("results/")
    folder_results.mkdir(parents=True, exist_ok=True)
    folder_results = str(folder_results)+"/"

    """
    TOPOLOGY from a json
    """
    t = Topology()
    t_json = create_json_topology()
    t.load(t_json)
    nx.write_gexf(t.G,folder_results+"graph_main1") # you can export the Graph in multiples format to view in tools like Gephi, and so on.

    """qos=LinearQoS(L=0.05,R=1.0))
    APPLICATION
    """
    app = create_application()

    """
    PLACEMENT algorithm
    """
    placement = CloudPlacement("onCloud") # it defines the deployed rules: module-device
    placement.scaleService({"ServiceA": 1}) 
    #In their case, the use a statical assignment.management_network.N[0][0] = (["utilization", "latency", "instructions"], ["instructions"])  # Cloud: ServiceA
    pop = Statical("Statical")
    #For each type of sink modules we set a deployment on some type of devices
    #A control sink consists on:
    #  args:
    #     model (str): identifies the device or devices where the sink is linked
    #     number (int): quantity of sinks linked in each device
    #     module (str): identifies the module from the app who r

    """
    POPULATION algorithm
    """
    #In ifogsim, during the creation of the application, the Sensors are assigned to the topology, in this case no. 
    # As mentioned, YAFS differentiates the adaptive sensors and their topological assignment.
    #In their case, the use a statical assignment.management_network.N[0][0] = (["utilization", "latency", "instructions"], ["instructions"])  # Cloud: ServiceA
    pop = Statical("Statical")
    #For each type of sink modules we set a deployment on some type of devices
    #A control sink consists on:
    #  args:
    #     model (str): identifies the device or devices where the sink is linked
    #     number (int): quantity of sinks linked in each device
    #     module (str): identifies the module from the app who receives the messages
    pop.set_sink_control({"model": "actuator-device",
                          "number":1,
                          "module": "Dashboard"}) # ILDE  app.get_sink_modules()})

    #In addition, a source includes a distribution function:
    dDistribution = deterministic_distribution(name="Deterministic",time=1)
    pop.set_src_control({"model": "sensor-device", 
                         "number":1,
                         "message": app.get_message("M.A"), 
                         "distribution": dDistribution})
    
    """--
    SELECTOR algorithm
    """
    #Their "selector" is actually the shortest way, there is not type of orchestration algorithm.
    #This implementation is already created in selector.class,called: First_ShortestPath
    selectorPath = MinimunPath()

    """
    SIMULATION ENGINE
    """

    stop_time = simulated_time
    sim = Sim(t, default_results_path=folder_results+"sim_trace")

    agent_configs_json = [
         {"node_id": 0,
          "agent_type": CloudAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 5*10*10**8,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [0,1],
          "metrics": {"service_node_utilization":{"module":"yafs.management_network", 
                                                 "class":"ServiceNodeUtilization",
                                                 "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{"bins": [0,20,40,60,80,100]}
                                                  }
                                                 },
                      "agent_node_utilization": {"module":"yafs.management_network", "class":"AgentNodeUtilization"},
                      "node_average_waiting_time": {"module":"yafs.management_network", 
                                                    "class":"NodeAverageWaitingTime",
                                                    "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{"bins": [0,200,400,600,800]}
                                                  }
                                                 },
                      "node_request_waiting_in": {"module":"yafs.management_network", "class":"NodeRequestsWaitingIn"},
                      "node_requests_out": {"module":"yafs.management_network", "class":"NodeRequestsOut"},
                      "net_buffer_size": {"module":"yafs.management_network", "class":"NetBufferSize"},
                      "node_nominalwatt": {"module":"yafs.management_network", "class":"NodeNominalWatt"},
                      "linear_cost_buyya": {"module":"yafs.management_network", 
                                            "class":"LinearCostBuyya",
                                            "params":{"cost_alpha": 1.0}
                                            },
                      "node_ipt":{"module":"yafs.management_network",
                                  "class":"NodeIPT",
                                  "post":{
                                        "module":"yafs.management_network",
                                        "class":"PostDiscretize",
                                        "params":{"bins": [300*10**5-1, 1*10*10**8-1, 10*10*10**8-1, 100*10*10**8-1, 1000*10*10**8-1]}
                                    }
                                  },
                     },
          "actions": {"msg_instructions_pctl": {"module":"yafs.management_network", 
                                                "class":"DiscretePercentileMessageInstructionsInterventions",
                                                "params": {"pctls": [0.1, 0.3, 0.5, 0.7, 1.0]},
                                               },
                      "discrete_node_ipt": {"module":"yafs.management_network", 
                                            "class":"DiscreteNodeIPTInterventions",
                                            "params": {"iptl":[300*10**5, 1*10*10**8, 10*10*10**8, 100*10*10**8]},
                                           },
                     }
         },
         {"node_id": 1,
          "agent_type": SensorAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 10**8,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [1,2],
          "metrics": {"service_node_utilization": {"module":"yafs.management_network", "class":"ServiceNodeUtilization"},
                      "agent_node_utilization": {"module":"yafs.management_network", "class":"AgentNodeUtilization"},
                      "node_average_waiting_time": {"module":"yafs.management_network", "class":"NodeAverageWaitingTime"},
                      "node_request_waiting_in": {"module":"yafs.management_network", "class":"NodeRequestsWaitingIn"},
                      "node_requests_out": {"module":"yafs.management_network", "class":"NodeRequestsOut"},
                      "net_buffer_size": {"module":"yafs.management_network", "class":"NetBufferSize"},
                      "node_nominalwatt": {"module":"yafs.management_network", "class":"NodeNominalWatt"},
                      "linear_cost_buyya": {"module":"yafs.management_network", 
                                            "class":"LinearCostBuyya",
                                            "params":{"cost_alpha": 1.0}
                                            }
                     }
         },
         {"node_id": 2,
          "agent_type": ActuatorAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 10*10*10**6,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [2,0],
          "metrics": {"service_node_utilization": {"module":"yafs.management_network", "class":"ServiceNodeUtilization"},
                      "agent_node_utilization": {"module":"yafs.management_network", "class":"AgentNodeUtilization"},
                      "node_average_waiting_time": {"module":"yafs.management_network", "class":"NodeAverageWaitingTime"},
                      "node_request_waiting_in": {"module":"yafs.management_network", "class":"NodeRequestsWaitingIn"},
                      "node_requests_out": {"module":"yafs.management_network", "class":"NodeRequestsOut"},
                      "net_buffer_size": {"module":"yafs.management_network", "class":"NetBufferSize"},
                      "node_nominalwatt": {"module":"yafs.management_network", "class":"NodeNominalWatt"},
                      "linear_cost_buyya": {"module":"yafs.management_network", 
                                            "class":"LinearCostBuyya",
                                            "params":{"cost_alpha": 1.0}
                                            }
                     }
         }
    ]

    management_network = ManagementAgentNetwork("management_network", agent_configs_json, sim)

    sim.deploy_app_agentic(app, placement, pop, selectorPath, management_network)

    """
    RUNNING - last step
    """
    sim.run(stop_time, show_progress_monitor=False)  # To test deployments put test_initial_deploy a TRUE
    sim.print_debug_assignaments()

    time_loops = [["M.A", "M.B"]]

    from yafs.stats import Stats
    mypath = "/home/ildefons/yaf310/examples/aif/results/sim_trace"

    m = Stats(defaultPath=mypath)
    m.showResults2(simulated_time, time_loops=time_loops)
    
    print("\t- Network saturation -")
    print("\t\tAverage waiting messages : %i" % m.average_messages_not_transmitted())
    print("\t\tPeak of waiting messages : %i" % m.peak_messages_not_transmitted())
    print("\t\tTOTAL messages not transmitted: %i" % m.messages_not_transmitted())

    print("\n\t- Stats of each service deployed -")
    print(m.get_df_modules())
    print(m.get_df_service_utilization("ServiceA",simulated_time))
    print(m.get_df_service_utilization("Camera",simulated_time))
    print(m.get_df_service_utilization("Dashboard",simulated_time))

    print("\n\t- Stats of each DEVICE -")

    app_name = "SimpleCase"
    app = sim.apps[app_name]
    services = app.services
    
    print("\n\t- Stats of each module deployed (except sources) -")
    print(m.get_df_modules())

    print("\n\t- Stats of each management agent deployed -")
    print(m.get_df_agent_modules())

    # for i in sim.management_network['management_network']['management_network'].agents.keys():
    #     agent_name = sim.management_network['management_network']['management_network'].agents[i].agent_name
    #     print("---------------------\n",agent_name)
    #     print(m.get_df_agent_utilization(agent_name,simulated_time))
    #     print(m.get_df_agent_sleeping_percentage(agent_name,simulated_time))
        
    #print(m.get_df_service_utilization("ServiceA",simulated_time))

    # s.draw_allocated_topology() # for debugging



if __name__ == '__main__':
    import logging.config
    import os

    logging.config.fileConfig(os.getcwd()+'/logging.ini')

    start_time = time.time()
    main(simulated_time=25500)

    print("\n--- %s seconds ---" % (time.time() - start_time))
