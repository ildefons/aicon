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
        n_f2 = len(self.metrics["node_average_waiting_time"].post.bins) + 1 # I add 1 becasue post-processing bins work like that
        self.state_factors = [n_f1, n_f2]
        self.n_state_factors = len(self.state_factors)

        self.obs_modalities = [n_f1, n_f2] # same observation as hidden states
        self.n_obs_modalities = len(self.obs_modalities)

        self.ACTIONS = list(range(len(self.actions['discrete_node_ipt'].iptl))) 
        self.n_actions = len(self.ACTIONS)

        # ---from pymdp import utils----------------------
        # Dirichlet priors (pseudo-counts)
        # -------------------------
        self.alpha_A = 1.0   # prior for A counts
        self.alpha_B = 1.0   # prior for B counts

        self.control_fac_idx = [0]

        #Make uniform A
        # A = utils.obj_array(self.n_obs_modalities)
        # for m, n_obs in enumerate(self.obs_modalities):
        #     A[m] = np.ones((n_obs, *self.state_factors)) * self.alpha_A # shape: (n_obs, n_f1, n_f2)
        #     # normalize over observation axis
        #     A[m] /= A[m].sum(axis=0, keepdims=True)

        # Make each hidden state map deterministically to one observation
        A = utils.obj_array(2)
        # Factor 0 100% deterministic
        # A[0] = np.zeros((n_f1, n_f1, n_f2))
        # for s1 in range(n_f1):
        #     # map each hidden state s1 to observation o=s1
        #     A[0][s1, s1, :] = 1.0
        # # normalize over observation axis
        # A[0] /= A[0].sum(axis=0, keepdims=True)
        #Factor 0 with some small noise
        A[0] = np.array([
            # o0 = 0
            [[1.0, 1.0],   
            [0.0, 0.0]],  
            # o0 = 1
            [[0.0, 0.0],  
            [1.0, 1.0]]  
        ])
        A[1] = np.array([
            # o1 = 0
            [[1.0, 0.0], 
            [1.0, 0.0]], 
            # o1 = 1
            [[0.0, 1.0], 
            [0.0, 1.0]] 
        ])
        # A[0] maps s0 → o0.
        # A[1] maps s1 → o1.


        # A[0] = np.zeros((n_f1, n_f1, n_f2)) #* 0.1
        # for s1 in range(n_f1):
        #     A[0][s1, s1, :] = 1.0#0.99
        # A[0] /= A[0].sum(axis=0, keepdims=True)

        # # Factor 1
        # A[1] = np.zeros((n_f2, n_f1, n_f2))
        # for s2 in range(n_f2):
        #     # map each hidden state s2 to observation o=s2
        #     A[1][s2, :, s2] = 1.0
        # A[1] /= A[1].sum(axis=0, keepdims=True)

        B = utils.obj_array(self.n_state_factors)
        # Factor 0: controlled → shape (n_f1, n_f1, n_actions)
        B[0] = np.ones((n_f1, n_f1, self.n_actions)) * self.alpha_B
        # Factor 1: uncontrolled → shape (n_f2, n_f2, 1)
        B[1] = np.ones((n_f2, n_f2, self.n_actions)) * self.alpha_B

        # -------------------------
        # Preferences (C) and initial state priors (D)
        # -------------------------
        # Very weak/flat preferences initially (agent indifferent)

        self.C = utils.obj_array(self.n_obs_modalities)
        for m, n_o in enumerate(self.obs_modalities):
            self.C[m] = np.ones(n_o) / n_o        

        self.D = utils.obj_array(self.n_state_factors)
        for m, n_s in enumerate(self.obs_modalities):
            self.D[m] = np.ones(n_s) / n_s  

        self.qs_prev = self.C.copy() # this is used in the update of self.B

        def normalize_B(B_dir):
            """Normalize each B_dir into probability matrices expected by pymdp."""
            B_norm = utils.obj_array(len(B_dir))
            for m, b_dir in enumerate(B_dir):
                # Normalize over columns for each slice along last axis
                for i in range(b_dir.shape[2]):
                    mat = b_dir[:, :, i]
                    col_sums = mat.sum(axis=0, keepdims=True)
                    col_sums[col_sums == 0] = 1.0  # avoid divide-by-zero
                    b_dir[:, :, i] = mat / col_sums
                B_norm[m] = b_dir
            return B_norm


        self.A_init = A.copy()
        self.B_init = normalize_B(B)
        self.pA = A.copy()
        self.pB = B.copy()
        
        # -------------------------
        # Create pymdp Agent with learning enabled
        # -------------------------
        #classpymdp.agent.Agent(A, B, C=None, D=None, E=None, H=None, pA=None, pB=None, pD=None, num_controls=None, policy_len=1, inference_horizon=1, control_fac_idx=None, policies=None, gamma=16.0, alpha=16.0, use_utility=True, use_states_info_gain=True, use_param_info_gain=False, action_selection='deterministic', sampling_mode='marginal', inference_algo='VANILLA', inference_params=None, modalities_to_learn='all', lr_pA=1.0, factors_to_learn='all', lr_pB=1.0, lr_pD=1.0, use_BMA=True, policy_sep_prior=False, save_belief_hist=False, A_factor_list=None, B_factor_list=None, sophisticated=False, si_horizon=3, si_policy_prune_threshold=0.0625, si_state_prune_threshold=0.0625, si_prune_penalty=512, ii_depth=10, ii_threshold=0.0625)
        self.pymdp_agent = Agent(
                    A=A.copy(),
                    B=normalize_B(B),
                    pA=A.copy(),
                    pB=B.copy(),
                    lr_pB = 10,
                    C=self.C,
                    D=self.D,
                    control_fac_idx = [0,1], # this is the (non-trivial) controllable factor: both 'discrete_node_ipt' and "waiting_time"
                    policy_len=1        # planning horizon (tweak as you like)
                    )
        
        self.prev_analog_wt = 0

    def one_hot_encode(self, wt, num_classes=4):
        return np.eye(1, num_classes, k=wt, dtype=int)[0]
    
    def agent_behavior(self, collected_metrics):
        """Retrieve and log incoming messages to cloud (node_id)."""

        wt = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == self.node_id][0]['value']
        ipt = [item for item in collected_metrics if item['metric'] == 'NodeIPT' and item['node_id'] == self.node_id][0]['value']
        wt_analog = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTimeAnalog' and item['node_id'] == self.node_id][0]['value']


        inc_wt = wt_analog - self.prev_analog_wt
        inc_wt_int = 1 #if no increase or decrease
        if inc_wt > 0:
            inc_wt_int = 0
        self.prev_analog_wt = wt_analog
        obs = [ipt, inc_wt_int]

        print("obs:",obs, inc_wt)

        #print("qs before:", [q.copy() for q in getattr(self.pymdp_agent, "qs", [])])
        
        #update posterior aprox of hidden states 

        qs = self.pymdp_agent.infer_states(obs)

        #print("qs after:", qs)
        
        #update A with the new observation (possible because before we infered qs: variational hidden state)
        #self.pymdp_agent.update_A(obs)  # I will do later

        myactions = self.actions['discrete_node_ipt']

        now = self.sim.env.now
        print(now)
        if now >= 0 and now < 500000: 
            # set C (goal observation distribution) to default uniform no prefference, so do nothing
            pass 

        elif now >= 500000 and now < 750000:
        #     # set C (goal observation distribution) preference to go to low waiting time
            self.pymdp_agent.C[1] = self.one_hot_encode(0, num_classes=self.obs_modalities[1])

        elif now >= 750000:
        #     # set C (goal observation distribution) preference to high waiting time
            self.pymdp_agent.C[1] = self.one_hot_encode(1, num_classes=self.obs_modalities[1]) 

        qs = self.pymdp_agent.infer_states(obs)

        self.pymdp_agent.update_A(obs)

        self.pymdp_agent.infer_policies()
        # sample action       
        next_action = None
        if now < 500000:
            aux = np.random.choice([0., 1.])
            next_action = np.array([aux,aux])
            next_action_aux = self.pymdp_agent.sample_action()  
        else:
            next_action = self.pymdp_agent.sample_action()  
        # apply action
        print("action:", next_action)
        
        myactions(action_id=int(next_action[0]), node_id=self.node_id)
        
        print("-------------")
        # update B 
        self.pymdp_agent.update_B(self.qs_prev)
        self.qs_prev = qs
        



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
          "sleep_time": 2000,  
          "instructions_per_wakeup": 5*10*10**8,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [0,1],
          "metrics": {"service_node_utilization":{"module":"yafs.management_network", 
                                                 "class":"ServiceNodeUtilization",
                                                 },
                      "agent_node_utilization": {"module":"yafs.management_network", "class":"AgentNodeUtilization"},
                      "node_average_waiting_time": {"module":"yafs.management_network", 
                                                    "class":"NodeAverageWaitingTime",
                                                    "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{"bins": [100]} #...-100 --->0
                                                                                  #101-... --->1
                                                                                
                                                  }
                                                 },
                      "node_average_waiting_time_analog": {"module":"yafs.management_network", 
                                                    "class":"NodeAverageWaitingTimeAnalog"},
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
                                        "params":{"bins": [300*10**5+1]} # <  300*10**5 ---> 0
                                                                         # >= 300*10**5+1 ---> 1
                                    }
                                  },
                     },
          "actions": {"discrete_node_ipt": {"module":"yafs.management_network", 
                                            "class":"DiscreteNodeIPTInterventions",
                                            "params": {"iptl":[300*10**5, 1000*10*10**10]},#, 10*10*10**8, 100*10*10**8]},
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
                      #"node_average_waiting_time": {"module":"yafs.management_network", "class":"NodeAverageWaitingTime"},
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
                      #"node_average_waiting_time": {"module":"yafs.management_network", "class":"NodeAverageWaitingTime"},
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
    main(simulated_time=1000000)

    print("\n--- %s seconds ---" % (time.time() - start_time))