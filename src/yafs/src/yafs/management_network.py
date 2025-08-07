import simpy
import numpy as np

import simpy
import numpy as np

import logging

import pandas as pd

# class ManagementAgent:
#     def __init__(self, sim, node_id, N, wake_up_interval, instructions_per_wakeup):
#         self.sim = sim
#         self.node_id = node_id  # Node where agent is colocated
#         self.N = N
#         self.wake_up_interval = wake_up_interval
#         self.instructions_per_wakeup = instructions_per_wakeup
#         self.message_queue = simpy.Store(self.sim.env)
#         self.logger = sim.logger
#         self.stop = False
#         #self.sim.env.process(self.run())

#     def run(self): # this is started by the ManagementAgentNetwork.
#         while True:
#             self.logger.info(f"Agent {self.node_id} waking at {self.sim.env.now}, colocated on node {self.node_id}")
#             yield self.sim.env.timeout(self.wake_up_interval)  # Sleep
#             self.logger.info(f"Agent {self.node_id} executing on node {self.node_id}")
#             yield self.sim.env.process(self.sim.process_agent_execution(self.node_id, self.instructions_per_wakeup))  # Execute
#             metrics = self.collect_metrics()
#             actions = self.get_management_actions(metrics)
#             self.apply_actions(actions)

#     def collect_metrics(self):
#         metrics = {
#             "node_utilization": {}, "message_latency": {}, "instructions": {},
#             "message_count": {}, "agent_execution_time": {}
#         }
#         for node in range(len(self.N)):
#             if "utilization" in self.N[self.node_id][node][0]:
#                 metrics["node_utilization"][node] = self.sim.topology.G.nodes[node].get("utilization", 0)
#             if "latency" in self.N[self.node_id][node][0]:
#                 metrics["message_latency"][node] = [
#                     entry["latency"] for entry in self.sim.metrics.data
#                     if entry["dst"] == node and "latency" in entry
#                 ]
#             if "instructions" in self.N[self.node_id][node][0]:
#                 metrics["instructions"][node] = {
#                     module: self.sim.apps[app].services[module]["instructions"]
#                     for app in self.sim.apps
#                     for modulclass ManagementAgentNetwork:
    
#     def __init__(self, name, agent_configs, activation_dist = None,logger=None):
#         self.logger = logger or logging.getLogger(__name__)
#         self.name = name
#         self.agent_configs =  agent_configs
#         self.activation_dist = activation_dist
#         # self.scaleServices = []

    
#     def get_next_activation(self):
#         """
#         Returns:
#             the next time to be activated
#         """
#         return self.activation_dist.next()

    
#     def initial_allocation(self,sim):#app_name):
#         """
#         Given an ecosystem, it starts the allocation of modules in the topology.

#         Args:
#             sim (:mod:yafs.core.Sim)
#             agent_configs (json object ) # app_name (String)

#         .. attention:: override required
#         """

#         # example of agent_configs:
#         # agent_configs = [
#         # (0, CloudAgent, 1000, 100000),  # Cloud agent
#         # (1, SensorAgent, 1000, 100000),  # Sensor agent
#         # (2, ActuatorAgent, 1000, 100000)]  # Actuator agent
                                                


#     def run(self,sim):
#         """
#         This method will be invoked during the simulation to change the assignment of the management agents to the topology

#         Args:.apps[app].services
#                     if self.sim.alloc_module.get(module, [None])[0] == node
#                 }
#             if "message_count" in self.N[self.node_id][node][0]:
#                 metrics["message_count"][node] = sum(1 for entry in self.sim.metrics.data if entry["dst"] == node)
#             if "agent_execution_time" in self.N[self.node_id][node][0]:
#                 metrics["agent_execution_time"][node] = sum(
#                     entry["execution_time"] for entry in self.sim.metrics.data
#                     if entry["node"] == node and entry["message"] == "AgentExecution"
#                 )
#         return metrics
    
#             sim (:mod: yafs.core.Sim)
#         """
#         self.logger.debug("Activiting - RUN - ManagementAgentnetwork")
#e in self.sim.apps[app].services
#                     if self.sim.alloc_module.get(module, [None])[0] == node
#                 }
#             if "message_count" in self.N[self.node_id][node][0]:
#                 metrics["message_count"][node] = sum(1 for entry in self.sim.metrics.data if entry["dst"] == node)
#             if "agent_execution_time" in self.N[self.node_id][node][0]:
#                 metrics["agent_execution_time"][node] = sum(
#                     entry["execution_time"] for entry in self.sim.metrics.data
#                     if entry["node"] == node and entry["message"] == "AgentExecution"
#                 )
#         return metrics
    
#     def get_management_actions(self, metrics):
#         return []

#     def apply_actions(self, actions):
#         for action in actions:
#             action_type = action[0]
#             if action_type == "set_message_instructions":
#                 _, app_name, msg_name, node, new_instructions = action
#                 if "message_instructions" in self.N[self.node_id][node][1]:
#                     if app_name in self.sim.apps and msg_name in self.sim.apps[app_name].messages:
#                         if new_instructions >= 10000000:  # Minimum instructions
#                             self.sim.apps[app_name].messages[msg_name]["instructions"] = new_instructions
#                             self.logger.info(f"Applied: Set {msg_name} instructions to {new_instructions} for node {node} in app {app_name}")
#                         else:
#                             self.logger.error(f"Invalid instructions {new_instructions} for {msg_name}")
#                     else:
#                         self.logger.error(f"Invalid app {app_name} or message {msg_name}")
#             else:
#                 self.logger.error(f"Unsupported action type: {action_type}")


# class ManagementAgentNetwork:
    
#     def __init__(self, name, agent_configs, activation_dist = None,logger=None):
#         self.logger = logger or logging.getLogger(__name__)
#         self.name = name
#         self.agent_configs =  agent_configs
#         self.activation_dist = activation_dist
#         # self.scaleServices = []

    
#     def get_next_activation(self):
#         """
#         Returns:
#             the next time to be activated
#         """
#         return self.activation_dist.next()

    
#     def initial_allocation(self,sim):#app_name):
#         """
#         Given an ecosystem, it starts the allocation of modules in the topology.

#         Args:
#             sim (:mod:yafs.core.Sim)
#             agent_configs (json object ) # app_name (String)

#         .. attention:: override required
#         """

#         # example of agent_configs:
#         # agent_configs = [
#         # (0, CloudAgent, 1000, 100000),  # Cloud agent
#         # (1, SensorAgent, 1000, 100000),  # Sensor agent
#         # (2, ActuatorAgent, 1000, 100000)]  # Actuator agent
                                                


#     def run(self,sim):
#         """
#         This method will be invoked during the simulation to change the assignment of the management agents to the topology

#         Args:.apps[app].services
#                     if self.sim.alloc_module.get(module, [None])[0] == node
#                 }
#             if "message_count" in self.N[self.node_id][node][0]:
#                 metrics["message_count"][node] = sum(1 for entry in self.sim.metrics.data if entry["dst"] == node)
#             if "agent_execution_time" in self.N[self.node_id][node][0]:
#                 metrics["agent_execution_time"][node] = sum(
#                     entry["execution_time"] for entry in self.sim.metrics.data
#                     if entry["node"] == node and entry["message"] == "AgentExecution"
#                 )
#         return metrics
    
#             sim (:mod: yafs.core.Sim)
#         """
#         self.logger.debug("Activiting - RUN - ManagementAgentnetwork")


# class ExampleAgentNetwork(ManagementAgentNetwork):
#     """
#     This implementation of ManagementAgentNetwork locates the agents in the corresponding device id according to "agent_configs".

#     It only runs once, in the initialization.

#     """
#     def initial_allocation(self, sim, app_name):
#         #We find the ID-nodo/resource
#         value = {"model": "Cluster"}
#         id_cluster = sim.topology.find_IDs(value) #there is only ONE Cluster
#         value = {"model": "m-"}
#         id_mobiles = sim.topology.find_IDs(value)

#         #Given an application we get its modules implemented
#         app = sim.apps[app_name]
#         services = app.services

#         for module in services.keys():
#             if "Coordinator" == module:
#                 if "Coordinator" in self.scaleServices.keys():
#                     # print self.scaleServices["Coordinator"]
#                     for rep in range(0,self.scaleServices["Coordinator"]):
#                         idDES = sim.deploy_module(app_name,module,services[module],id_cluster) #Deploy as many modules as elements in the array

#             elif "Calculator" == module:
#                 if "Calculator" in self.scaleServices.keys():
#                     for rep in range(0, self.scaleServices["Calculator"]):
#                         idDES = sim.deploy_module(app_name,module,services[module],id_cluster)

#             elif "Client" == module:
#                 idDES = sim.deploy_module(app_name,module, services[module],id_mobiles)import simpy
import numpy as np

import simpy
import numpy as np

import logging

class ManagementAgent:
    def __init__(self, 
                 sim, 
                 node_id, 
                 DES_id, 
                 agent_name, 
                 N, 
                 sleep_time, 
                 instructions_per_wakeup, 
                 agent_ipt_percentage,
                 observable_node_ids):
        self.sim = sim
        self.node_id = node_id  # Node where agent is colocated
        self.DES_id = DES_id # Id of the DES process for this agent 
        self.agent_name = agent_name # agent name: agent_name = "agent_" + "node" + str(node_id) + "_" + agent_type.__name__
        self.N = N
        self.sleep_time = sleep_time
        self.instructions_per_wakeup = instructions_per_wakeup
        self.message_queue = simpy.Store(self.sim.env)
        self.logger = sim.logger
        self.stop = False
        self.agent_ipt_percentage = agent_ipt_percentage # this percentage is used when updating node metrics to compute the used instructions by both the agent and the module running in the same node_id
        self.observable_node_ids = observable_node_ids

        self.last_time_agent_start_processing = -1 # we should retrieve all agent events that happened [self.last_time_agent_start_processing, end_of_sleeping]


    def run(self):
        #Registering the DES process into the simulator
        self.sim.des_process_running[self.DES_id] = True
        self.sim.des_control_process[self.agent_name] = self.DES_id

        self.logger.debug("Added_Process - Local Agent Management Algorithm\t#DES:%i" % self.DES_id)
        
        while not self.stop and self.sim.des_process_running[self.DES_id]:
            #Simulated wake up/oeration cycle
            self.logger.info(f"Agent {self.node_id} waking at {self.sim.env.now}, colocated on node {self.node_id}")
            time_sleep_start = self.sim.env.now
            yield self.sim.env.timeout(self.sleep_time)  # Sleep
            time_sleep_end = self.sim.env.now
            self.logger.info(f"Agent {self.node_id} executing on node {self.node_id}")

            #Real logic of the management agent
            <-----IMHERE
            metrics_df = self.collect_metrics(self.last_time_agent_start_processing, time_sleep_end)
            self.last_time_agent_start_processing = time_sleep_end # update for next iteration
            actions = self.get_management_actions(metrics_df)   # main method to be customized
            self.apply_actions(actions)

            #Compute time working as self.instructions_per_wakeup/float(node["IPT"])  
            att_node = self.sim.topology.G.nodes[self.node_id]
            available_ipt = self.agent_ipt_percentage * float(att_node["IPT"])  #available IPT is divided between colocated agent and app module
            time_of_service = self.instructions_per_wakeup / available_ipt  #float(att_node["IPT"])
            
            #Simulate agent' time of service
            yield self.sim.env.timeout(time_of_service) # Work 
            time_processing_end = self.sim.env.now           

            #Update agent metrics
            self.sim.metrics.insert_agent_step({
                         "type": self.sim.AGENT_METRIC,
                         "node_id": self.node_id,
                         "DES_id": self.DES_id, 
                         "agent_name": self.agent_name,                # print("Inside _update_node_metrics")
                # print("id_node:", id_node)
                # # check whether this node has a running agent
                # agent_node_ids = [config[0] for config in self.management_network['management_network']['management_network'].agent_configs]
                # print(agent_node_ids)
                # position = -1
                # try:
                #     position = agent_node_ids.index(id_node)
                # except ValueError:
                #     pass
                # print("_____",position)
                         "time_sleep_start": time_sleep_start,
                         "time_sleep_end": time_sleep_end,
                         "sleeping_time": float(time_sleep_end-time_sleep_start),
                         "time_processing_end": time_processing_end,
                         "service": float(time_processing_end-time_sleep_end)
                         })
            # print("------------------------")
            # print("agent_name:", self.agent_name)
            # print("time sleeping:",self.wake_up_interval)
            # print("time sleeping (with now):",float(time_sleep_end-time_sleep_start))
            # print("time_of_service:",time_of_service)
            # print("time_of_service (with now):",time_processing_end-time_sleep_end)

        self.logger.debug("STOP_Process - Placement Algorithm\t#DES:%i" % self.DES_id)
        

    def collect_metrics(self, time_limit):
        # metrics = {
        #     "node_utilization": {}, "message_latency": {}, "instructions": {},
        #     "message_count": {}, "agent_execution_time": {}
        # }
        event_df = None
        filtered_df = None
        try:
            event_df = self.sim.metrics.get_event_dataframe_since("app",self.last_metric_id + 1, max_rows=10**6) #read 10^6 ("all") rows since last time

            app_event_df = self.sim.metrics.get_event_dataframe_where_time_out_gt(metric_type="app", 
                                                                                 time_start_ok=self.last_time_agent_start_sleeping,
                                                                                 time_th_ok=time_limit, 
                                                                                 max_rows=10**6)
            app_event_df2 = self.sim.metrics.get_event_dataframe_where_time_out_gt(metric_type="app", 
                                                                                 time_start_ok=self.last_time_agent_start_sleeping,
                                                                                 time_th_ok=time_limit+10000000, 
                                                                                 max_rows=10**6)
            print(app_event_df.shape[0],app_event_df2.shape[0])
            #:self.sim.metrics.get_event_dataframe_since(self.last_metric_id + 1, max_rows=10*6)

        except IndexError as e:
            print("Error: Entry index is out of bounds.")
        except Exception as e:
            print("Unexpected error:", str(e))
         
        if event_df is not None:
            event_df['TOPO.dst'] = pd.to_numeric(event_df['TOPO.dst'], errors='coerce')
            event_df['id'] = pd.to_numeric(event_df['id'], errors='coerce')
            self.last_metric_id = int(event_df['id'].max()) # updates the top metric id read so far 

            filtered_df = event_df[event_df['TOPO.dst'].isin(self.observable_node_ids)]
            # print("event_df.shape", event_df.shape)
            # print("self.observable_node_ids", self.observable_node_ids)
            # print("filtered_df[\"TOPO.dst\"]",filtered_df["TOPO.dst"])

        #<---IMHERE: collect metrics since last collection

        # for node in range(len(self.N)):
        #     if "utilization" in self.N[self.node_id][node][0]:
        #         metrics["node_utilization"][node] = self.sim.topology.G.nodes[node].get("utilization", 0)
        #     if "latency" in self.N[self.node_id][node][0]:
        #         metrics["message_latency"][node] = [
        #             entry["latency"] for entry in self.sim.metrics.data
        #             if entry["dst"] == node and "latency" in entry
        #         ]
        #     if "instructions" in self.N[self.node_id][node][0]:
        #         metrics["instructions"][node] = {
        #             module: self.sim.apps[app].services[module]["instructions"]
        #             for app in self.sim.apps
        #             for module in self.sim.apps[app].services
        #             if self.sim.alloc_module.get(module, [None])[0] == node
        #         }
        #     if "message_count" in self.N[self.node_id][node][0]:
        #         metrics["message_count"][node] = sum(1 for entry in self.sim.metrics.data if entry["dst"] == node)
        #     if "agent_execution_time" in self.N[self.node_id][node][0]:
        #         metrics["agent_execution_time"][node] = sum(
        #             entry["execution_time"] for entry in self.sim.metrics.data
        #             if entry["node"] == node and entry["message"] == "AgentExecution"
        #         )
        return filtered_df
    
    def get_management_actions(self, metrics):
        return []

    def apply_actions(self, actions):
        
        for action in actions:
            action_type = action[0]
            if action_type == "set_message_instructions":
                _, app_name, msg_name, node, new_instructions = action
                if "message_instructions" in self.N[self.node_id][node][1]:
                    if app_name in self.sim.apps and msg_name in self.sim.apps[app_name].messages:
                        if new_instructions >= 10000000:  # Minimum instructions
                            self.sim.apps[app_name].messages[msg_name]["instructions"] = new_instructions
                            self.logger.info(f"Applied: Set {msg_name} instructions to {new_instructions} for node {node} in app {app_name}")
                        else:
                            self.logger.error(f"Invalid instructions {new_instructions} for {msg_name}")
                    else:
                        self.logger.error(f"Invalid app {app_name} or message {msg_name}")
            else:
                self.logger.error(f"Unsupported action type: {action_type}")


class ManagementAgentNetwork:
    
    def __init__(self, name, agent_configs_json, sim, activation_dist = None,logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.name = name
        self.agent_configs_json =  agent_configs_json
        self.sim = sim
        self.activation_dist = activation_dist
        self.agents = {}
        # self.scaleServices = []

    
    def get_next_activation(self):
        """
        Returns:
            the next time to be activated
        """
        return self.activation_dist.next()

    
    def initial_allocation(self,sim,app_name):
        """
        Given an ecosystem, it starts the allocation of modules in the topology.

        Args:
            sim (:mod:yafs.core.Sim)
            agent_configs (json object ) # app_name (String)

        .. attention:: override required
        """

        for agent_json in self.agent_configs_json:
            node_id = agent_json["node_id"]
            agent_type = agent_json["agent_type"]
            sleep_time = agent_json["sleep_time"]
            instructions_per_wakeup = agent_json["instructions_per_wakeup"]
            agent_ipt_percentage = agent_json["agent_ipt_percentage"]
            observable_node_ids = agent_json["observable_node_ids"]
            N = [] # ILDE: TBD
            myId = self.sim._Sim__get_id_process()#__get_id_process() is private so I overcome the privatenss explicitly (not nice)
            agent_name = "agent_" + "node" + str(node_id) + "_" + agent_type.__name__

            #make sure agent_ipt_percentage is within range [0,1]. If not floor it between [0,1] + log a warning
            agent_ipt_percentage_01 = max(0, min(1, agent_ipt_percentage))

            observable_node_ids = agent_json["observable_node_ids"]
            agent = agent_type(self.sim, node_id, myId, agent_name, N, sleep_time, instructions_per_wakeup, 
                               agent_ipt_percentage_01, observable_node_ids)
            self.agents[node_id] = agent
            # start gant process        

            self.sim.env.process(agent.run())
            # Note: agent registration, logging and metrics saving is done in the agent run() method in each iteration wake up 

            """
            DES-process who controls the invocation of a management agent
            """
            self.sim.des_process_running[myId] = True
            self.sim.des_control_process[agent_name] = myId

            # ---> log actions
            # ---> within agent run() I need logs and record events
        # example of agent_configs:
        # agent_configs = [
        # (0, CloudAgent, 1000, 100000),  # Cloud agent
        # (1, SensorAgent, 1000, 100000),  # Sensor agent
        # (2, ActuatorAgent, 1000, 100000)]  # Actuator agent
                                                


    def run(self,sim):
        """
        This method will be invoked during the simulation to change the assignment of the management agents to the topology

        Args:
            sim (:mod: yafs.core.Sim)
        """
        self.logger.debug("Activiting - RUN - ManagementAgentnetwork")


# class ExampleAgentNetwork(ManagementAgentNetwork):
#     """
#     This implementation of ManagementAgentNetwork locates the agents in the corresponding device id according to "agent_configs".

#     It only runs once, in the initialization.

#     """
#     def initial_allocation(self, sim, app_name):
#         #We find the ID-nodo/resource
#         value = {"model": "Cluster"}
#         id_cluster = sim.topology.find_IDs(value) #there is only ONE Cluster
#         value = {"model": "m-"}
#         id_mobiles = sim.topology.find_IDs(value)

#         #Given an application we get its modules implemented
#         app = sim.apps[app_name]
#         services = app.services

#         for module in services.keys():
#             if "Coordinator" == module:
#                 if "Coordinator" in self.scaleServices.keys():
#                     # print self.scaleServices["Coordinator"]
#                     for rep in range(0,self.scaleServices["Coordinator"]):
#                         idDES = sim.deploy_module(app_name,module,services[module],id_cluster) #Deploy as many modules as elements in the array

#             elif "Calculator" == module:
#                 if "Calculator" in self.scaleServices.keys():
#                     for rep in range(0, self.scaleServices["Calculator"]):
#                         idDES = sim.deploy_module(app_name,module,services[module],id_cluster)

#             elif "Client" == module:
#                 idDES = sim.deploy_module(app_name,module, services[module],id_mobiles)