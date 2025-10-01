"""
    Scenario: node 1) model builder , nodes 2,3) gradient computing workers
              node 1) observes all nodes, nodes 2,3) observe themself only
              node 1) can modify the qos of any worker node, nodes 2,3) can modify ther own ipt only
              node 0) is the source of data minibatch work packages: m0
              data flow architecture:
              0)---m0--->1)---m1--->2)3)---m2--->1)
              m0: generation of new mini-batch: 0)--->1)
              m1: request for gradient computation: 1)--->2)3)
              m2: request for model integation: 2)3)---1)


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


# Custom agent classes
class ServiceLeaderAgent(ManagementAgent):
    def __custom_init__(self):
        self.state_id = 0


    def agent_behavior(self, collected_metrics):
        """Retrieve and log incoming messages to cloud (node_id)."""

        print("inside ServiceLeaderAgent")
        wt3 = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == 3][0]['value']
        wt4 = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == 4][0]['value']
        print("wt3: ", wt3, ", wt4:", wt4)
        
        # if worker 1 + 2 (mean) wt > 500 and high qos, lower qos

        # if worker 1 + 2 (mean) wt <= 500 and low qos, raise qos

        # Motivaion: first the Leader tries to control wt by adjusting qos for all workers, if this fails, individual workers will raise/low locl ipt/resources
        # Why: Goal try to see distributed control, oscilations, different regimes

        # myactions2 = self.actions['discrete_node_ipt']
        
        # if self.sim.env.now >= 2000 and self.state_id == 0:
        #     self.state_id = 1
        #     myactions2(action_id=1, node_id=self.node_id)
        # elif self.sim.env.now >= 4000 and self.state_id == 1:
        #     self.state_id = 2
        #     myactions2(action_id=0, node_id=self.node_id)
        # elif self.state_id == 2:
        #     sublist_metrics = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == self.node_id]
        #     if sublist_metrics[0]['value'] > 550:
        #         myactions2(action_id=1, node_id=self.node_id)  #We move to high performance
        #     if sublist_metrics[0]['value'] < 200:
        #         myactions2(action_id=0, node_id=self.node_id)  #We move to low performance          


class WorkerAgent(ManagementAgent):
    def agent_behavior(self, collected_metrics):
        """Sensor monitors metrics (no actions for now)."""

        print("inside WorkerAgent")
        wt = [item for item in collected_metrics if item['metric'] == 'NodeAverageWaitingTime' and item['node_id'] == self.node_id][0]['value']
        print("wt: ", wt)

        # if worker wt > 1000 and lower tier ipt, increase ipt

        # if worker wt <= 1000 and high tier ipt, lower ipt

        return []  # Extensible for future logic



class MinimunPath(Selection):

    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):

        """
        Computes the minimun path among the source elemento of the topology and the localizations of the module

        Return the path and the identifier of the module deployed in the last element of that path
        """
        node_src = topology_src
        DES_dst = alloc_module[app_name][message.dst]
        # if message.dst == "ServiceWorker":
        #     print(3)
        # print(("GET PATH"))
        # print(("\tNode _ src (id_topology): %i" %node_src))
        # print(("\tRequest service: %s " %message.dst))
        # print(("\tProcess serving that service: %s " %DES_dst))

        bestPath = []
        bestDES = []

        #ILDE: if more than 1 instance of the target module, I pick 1 randomly so I prevent the same instance being called all the time
        if len(DES_dst) > 1:
            aux = [random.choice(DES_dst)]
            DES_dst = aux    

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


class FederatedPlacement(Placement):
    """
    This implementation locates the services of the application 
    in the cheapest cloud regardless of where the sources or sinks are located.

    It only runs once, in the initialization.

    """
    def initial_allocation(self, sim, app_name):
        #We find the ID-nodo/resource

        app = sim.apps[app_name]
        services = app.services

        id_cluster1 = [1]
        module1 = 'ServiceLeader1'
        idDES1 = sim.deploy_module(app_name,module1,services[module1],id_cluster1)

        id_cluster2 = [2]
        module2 = 'ServiceLeader2'
        idDES2 = sim.deploy_module(app_name,module2,services[module2],id_cluster2)

        id_cluster3 = [3]
        module3 = 'ServiceWorker'
        idDES3 = sim.deploy_module(app_name,module3,services[module3],id_cluster3)  
        id_cluster4 = [4]
        idDES4 = sim.deploy_module(app_name,module3,services[module3],id_cluster4)  # NOTE: 3 types of services but 4 deployed instances (1 leader1, 1 leader2, 2 workers)
    #end function

RANDOM_SEED = 1

def create_application():
    # APLICATION
    a = Application(name="FederatedLearning")

    # # (Camera) --> (ServiceA) --> (dashboard)
    # a.set_modules([{"Camera":{"Type":Application.TYPE_SOURCE}},
    #                {"ServiceA": {"RAM": 10, "Type": Application.TYPE_MODULE}},
    #                {"Dashboard": {"Type": Application.TYPE_SINK}}
    #               ])
    
    # 0)---m0--->1)---m1--->2)3)---m2--->1)
    # m0: generation of new mini-batch: 0)--->1)
    # m1: request for gradient computation: 1)--->2)3)
    # m2: request for model integation: 2)3)---1)

    a.set_modules([{"MinibatchCreator":{"Type":Application.TYPE_SOURCE}},
                   {"ServiceLeader1": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"ServiceLeader2": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"ServiceWorker": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"Dashboard": {"Type": Application.TYPE_SINK}}
                  ])


    m_0 = Message("M0", "MinibatchCreator", "ServiceLeader1", instructions=20*10**5, bytes=1000, qos=LinearQoS(L=0.05,R=1.0))
    m_1 = Message("M1", "ServiceLeader1", "ServiceWorker",instructions=20*10**5, bytes=1000)
    m_2 = Message("M2", "ServiceWorker", "ServiceLeader2", instructions=20*10**5, bytes=1000)
    m_3 = Message("M3", "ServiceLeader2", "Dashboard", instructions=20*10**3, bytes=1000)

    # """
    # Messages among MODULES (AppEdge in iFogSim)
    # """
    
    # m_a = Message("M.A", "Camera", "ServiceA", instructions=20*10**6, bytes=1000, qos=LinearQoS(L=0.05,R=1.0))   
    # # ILDE: I have added new attribute qos so I can monitor and control the QoS of this message
    # m_b = Message("M.B", "ServiceA", "Dashboard", instructions=30*10**6, bytes=500)

    """
    Defining which messages will be dynamically generated # the generation is controlled by Population algorithm
    """
    #a.add_source_messages(m_a)
    a.add_source_messages(m_0)

    """
    MODULES/SERVICES: Definition of Generators and Consumers 
    """
    # MODULE SERVICES
    #a.add_service_module("ServiceA", m_a, m_b, fractional_selectivity, threshold=1.0)
    a.add_service_module("ServiceLeader1", m_0, m_1, fractional_selectivity, threshold=1.0)
    a.add_service_module("ServiceWorker", m_1, m_2, fractional_selectivity, threshold=1.0)
    a.add_service_module("ServiceLeader2", m_2, m_3, fractional_selectivity, threshold=1.0)


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

    # cloud_dev    = {"id": 0, "model": "cloud","mytag":"cloud", "IPT": 300 * 10 ** 5, "RAM": 40000,"COST": 3,"WATT":20.0}
    # sensor_dev   = {"id": 1, "model": "sensor-device", "IPT": 100* 10 ** 6, "RAM": 4000,"COST": 3,"WATT":40.0}
    # actuator_dev = {"id": 2, "model": "actuator-device", "IPT": 100 * 10 ** 7, "RAM": 4000,"COST": 3, "WATT": 40.0}

    minibatch_creator_dev    = {"id": 0, "model": "mb_dev","mytag":"mb_dev", "IPT": 100 * 10 ** 6, "RAM": 40000,"COST": 3,"WATT":40.0}
    service_leader_dev1   = {"id": 1, "model": "service-leader-device","mytag":"service-leader-device", "IPT": 100* 10 ** 6, "RAM": 4000,"COST": 3,"WATT":40.0}
    service_leader_dev2   = {"id": 2, "model": "service-leader-device","mytag":"service-leader-device", "IPT": 100* 10 ** 6, "RAM": 4000,"COST": 3,"WATT":40.0}
    service_worker_dev1   = {"id": 3, "model": "service-worker-device","mytag":"service-worker-device", "IPT": 10* 10 ** 5, "RAM": 4000,"COST": 3,"WATT":40.0}
    service_worker_dev2   = {"id": 4, "model": "service-worker-device","mytag":"service-worker-device", "IPT": 10* 10 ** 5, "RAM": 4000,"COST": 3,"WATT":40.0}
    dashboard_dev   = {"id": 5, "model": "dashboard-device", "mytag":"dashboard-device","IPT": 100* 10 ** 6, "RAM": 4000,"COST": 3,"WATT":40.0}

    link1 = {"s": 0, "d": 1, "BW": 1, "PR": 1}  #MBSource--->Leader1
    link2 = {"s": 1, "d": 3, "BW": 1, "PR": 1}  #Leader1--->Worker1     
    link3 = {"s": 1, "d": 4, "BW": 1, "PR": 1}  #Leader1--->Worker2
    link4 = {"s": 3, "d": 2, "BW": 1, "PR": 1}  #Worker1--->Leader2
    link5 = {"s": 4, "d": 2, "BW": 1, "PR": 1}  #Worker2--->leader2
    link6 = {"s": 2, "d": 5, "BW": 1, "PR": 1}  #leader2--->Dashboard

    topology_json["entity"].append(minibatch_creator_dev)
    topology_json["entity"].append(service_leader_dev1)
    topology_json["entity"].append(service_leader_dev2)
    topology_json["entity"].append(service_worker_dev1)
    topology_json["entity"].append(service_worker_dev2)
    topology_json["entity"].append(dashboard_dev)
    topology_json["link"].append(link1)
    topology_json["link"].append(link2)
    topology_json["link"].append(link3)
    topology_json["link"].append(link4)
    topology_json["link"].append(link5)
    topology_json["link"].append(link6)

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
    
    placement = FederatedPlacement("fl") # it defines the deployed rules: module-device

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
    pop.set_sink_control({"model": "dashboard-device",
                          "number":1,
                          "module": "Dashboard"}) # ILDE  app.get_sink_modules()})

    #In addition, a source includes a distribution function:
    dDistribution = deterministic_distribution(name="Deterministic",time=1)
    pop.set_src_control({"model": "mb_dev",#sensor-device", 
                         "number":1,
                         "message": app.get_message("M0"), 
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
         {"node_id": 1,
          "agent_type": ServiceLeaderAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 5*10**6,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [0,1,2,3,4,5],
          "metrics": {"service_node_utilization":{"module":"yafs.management_network", 
                                                 "class":"ServiceNodeUtilization",
                                                 "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{
                                                         "bins": [0,20,40,60,80,100]                                                           
                                                     }
                                                  }
                                                 },
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
                     },
          "actions": {"msg_instructions_pctl": {"module":"yafs.management_network", 
                                                "class":"DiscretePercentileMessageInstructionsInterventions",
                                                "params": {"pctls": [0.1, 0.3, 0.5, 0.7, 1.0]},
                                               }
                     }
         },
         {"node_id": 3,
          "agent_type": WorkerAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 5*10**6,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [3],
          "metrics": {"service_node_utilization":{"module":"yafs.management_network", 
                                                 "class":"ServiceNodeUtilization",
                                                 "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{
                                                         "bins": [0,20,40,60,80,100]                                                           
                                                     }
                                                  }
                                                 },
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
                     },
          "actions": {"discrete_node_ipt": {"module":"yafs.management_network", 
                                            "class":"DiscreteNodeIPTInterventions",
                                            "params": {"iptl":[10**5, 10**7]},
                                           },
                     }
         },
         {"node_id": 4,
          "agent_type": WorkerAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 5*10**6,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [4],
          "metrics": {"service_node_utilization":{"module":"yafs.management_network", 
                                                 "class":"ServiceNodeUtilization",
                                                 "post":{
                                                     "module":"yafs.management_network",
                                                     "class":"PostDiscretize",
                                                     "params":{
                                                         "bins": [0,20,40,60,80,100]                                                           
                                                     }
                                                  }
                                                 },
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
                     },
          "actions": {"discrete_node_ipt": {"module":"yafs.management_network", 
                                            "class":"DiscreteNodeIPTInterventions",
                                            "params": {"iptl":[10**5, 10**7]},
                                           },
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

    time_loops = [["M1", "M2"]]

    from yafs.stats import Stats
    #mypath = "/home/ildefons/yaf310/examples/aif/results/sim_trace"
    mypath = "/home/ildefons/yaf310/examples/ayafs/FederatedLearning/results/sim_trace"

    m = Stats(defaultPath=mypath)
    m.showResults2(simulated_time, time_loops=time_loops)
    
    print("\t- Network saturation -")
    print("\t\tAverage waiting messages : %i" % m.average_messages_not_transmitted())
    print("\t\tPeak of waiting messages : %i" % m.peak_messages_not_transmitted())
    print("\t\tTOTAL messages not transmitted: %i" % m.messages_not_transmitted())

    print("\n\t- Stats of each service deployed -")
    print(m.get_df_modules())
    print(m.get_df_service_utilization("ServiceLeader1",simulated_time))
    print(m.get_df_service_utilization("ServiceLeader2",simulated_time))
    print(m.get_df_service_utilization("Servicewoker",simulated_time))
    print(m.get_df_service_utilization("Dashboard",simulated_time))

    print("\n\t- Stats of each DEVICE -")

    app_name = "FederatedLearning"
    app = sim.apps[app_name]
    services = app.services
    
    print("\n\t- Stats of each module deployed (except sources) -")
    print(m.get_df_modules())

    print("\n\t- Stats of each management agent deployed -")
    print(m.get_df_agent_modules())



if __name__ == '__main__':
    import logging.config
    import os

    logging.config.fileConfig(os.getcwd()+'/logging.ini')

    start_time = time.time()
    main(simulated_time=10000)

    print("\n--- %s seconds ---" % (time.time() - start_time))
