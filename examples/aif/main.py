"""
    Scenario: Evaluation section of paper "Equilibrium in the Computing Continuum through Active Inference"

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
from yafs.management_network import ManagementAgent, ManagementAgentNetwork, DiscretePercentileInterventions
import simpy
import numpy as np


# Custom agent classes
class CloudAgent(ManagementAgent):
    def __custom_init__(self):
        self.myactions = DiscretePercentileInterventions(agent = self, 
                                                    sim = self.sim, 
                                                    des_id = self.DES_id, 
                                                    pctls = [0.1, 0.3, 0.5, 0.7, 1.0])
        self.action_id = 0


    def agent_behavior(self, collected_metrics):
        """Retrieve and log incoming messages to cloud (node_id)."""

        #print("CloudAgent.get_management_action()")

        #get the des_id of the service running in the same node of the agent
        def get_key_by_value(d, x):
            for k, v in d.items():
                if v == x:
                    return k
            raise ValueError(f"Value {x} not found in dictionary")
        service_des_id = get_key_by_value(self.sim.alloc_DES, self.node_id)
        
        #apply action to service with id = service_des_id
        self.myactions(self.action_id, service_des_id = service_des_id)
        #rotate action for next time
        self.action_id = self.action_id + 1
        if self.action_id >= len(self.myactions.pctls):
            self.action_id = 0
        

        actions = []
        # incoming_messages = [
        #     entry for entry in self.sim.metrics.data
        #     if entry["dst"] == self.node_id and "message" in entry
        # ]
        # for msg in incoming_messages:
        #     self.logger.info(f"CloudAgent: Incoming message {msg['message']} to node {self.node_id}, "
        #                      f"latency: {msg.get('latency', 'N/A')}, instructions: {msg.get('instructions', 'N/A')}")
        return actions

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
        Computes the minimun path https://es.aliexpress.com/item/1005009035988189.html?spm=a2g0o.detail.pcDetailTopMoreOtherSeller.5.774fH4pAH4pAHb&gps-id=pcDetailTopMoreOtherSeller&scm=1007.40050.354490.0&scm_id=1007.40050.354490.0&scm-url=1007.40050.354490.0&pvid=ca075d23-95fb-4777-b411-f42e198e2e62&_t=gps-id:pcDetailTopMoreOtherSeller,scm-url:1007.40050.354490.0,pvid:ca075d23-95fb-4777-b411-f42e198e2e62,tpp_buckets:668%232846%238113%231998&pdp_ext_f=%7B%22order%22%3A%22540%22%2C%22eval%22%3A%221%22%2C%22sceneId%22%3A%2230050%22%7D&pdp_npi=4%40dis%21EUR%213.19%213.19%21%21%2126.19%2126.19%21%40211b80c217534334445801854e3298%2112000047666434150%21rec%21ES%21800113694%21XZ&utparam-url=scene%3ApcDetailTopMoreOtherSeller%7Cquery_from%3Aamong the source elemento of the topology and the localizations of the module

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
                   {"Dashboard": {"Type": Application.TYPE_SINK}},
                   {"Dashboard2": {"Type": Application.TYPE_SINK}},
                   ])
    """
    Messages among MODULES (AppEdge in iFogSim)
    """
    
    m_a = Message("M.A", "Camera", "ServiceA", instructions=20*10**6, bytes=1000, qos=LinearQoS(L=0.5,R=1.0))   #ILDE: I have added new attribute qos so I can monitor and control the QoS of this message
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

    cloud_dev    = {"id": 0, "model": "cloud","mytag":"cloud", "IPT": 5000 * 10 ** 3, "RAM": 40000,"COST": 3,"WATT":20.0}
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

    """
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
    #sim.deploy_app2(app, placement, pop, selectorself.sim.topology.get_info()[0]["WATT"]Path)
   

    #ILDE: declaration of my management network
    # agent_configs_json = [
        #  {"node_id": 0,
        #   "agent_type": CloudAgent,
        #   "sleep_time": 10,  
        #   "instructions_per_wakeup": 5*10*10**8,
        #   "agent_ipt_percentage": 0.5  #percentage of the node CPU/GPU reserved for the management agent. Needed to compute "service_time" when updating metrics 
        #  },
    # ]
    agent_configs_json = [
         {"node_id": 0,
          "agent_type": CloudAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 5*10*10**8,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [0,1],
          "metrics": {"service_node_utilization": "ServiceNodeUtilization",
                      "agent_node_utilization": "AgentNodeUtilization",
                      "node_average_waiting_time": "NodeAverageWaitingTime",
                      "node_request_waiting_in": "NodeRequestsWaitingIn",
                      "node_requests_out": "NodeRequestsOut",
                      "net_buffer_size": "NetBufferSize",
                      "node_nominalwatt": "NodeNominalWatt",
                      "linear_cost_buyya": "LinearCostBuyya"
                     },
          "cost_alpha": 1.0
         },
         {"node_id": 1,
          "agent_type": SensorAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 10**8,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [1,2],
          "metrics": {"service_node_utilization": "ServiceNodeUtilization",
                      "agent_node_utilization": "AgentNodeUtilization",
                      "node_average_waiting_time": "NodeAverageWaitingTime",
                      "node_request_waiting_in": "NodeRequestsWaitingIn",
                      "node_requests_out": "NodeRequestsOut",
                      "net_buffer_size": "NetBufferSize",
                      "node_nominalwatt": "NodeNominalWatt",
                      "linear_cost_buyya": "LinearCostBuyya"
                     },
          "cost_alpha": 1.0
         },
         {"node_id": 2,
          "agent_type": ActuatorAgent,
          "sleep_time": 500,  
          "instructions_per_wakeup": 10*10*10**6,
          "agent_ipt_percentage": 0.5,
          "observable_node_ids": [2,0],
          "metrics": {"service_node_utilization": "ServiceNodeUtilization",
                      "agent_node_utilization": "AgentNodeUtilization",
                      "node_average_waiting_time": "NodeAverageWaitingTime",
                      "node_request_waiting_in": "NodeRequestsWaitingIn",
                      "node_requests_out": "NodeRequestsOut",
                      "net_buffer_size": "NetBufferSize",
                      "node_nominalwatt": "NodeNominalWatt",
                      "linear_cost_buyya": "LinearCostBuyya"
                     },
          "cost_alpha": 1.0
         }
    ]

    management_network = ManagementAgentNetwork("management_network", agent_configs_json, sim)
    # Set matrix N for your 3-node case
    # management_network.N[0][0] = (["utilization", "latency", "instructions"], [])  # Cloud: ServiceA
    # management_network.N[1][1] = (["utilization"], [])  # Sensor: Camera
    # management_network.N[2][2] = (["latency"], [])  # Actuator: Dashboard
    #ILDE: end of MN declaration

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
    main(simulated_time=15500)

    print("\n--- %s seconds ---" % (time.time() - start_time))
