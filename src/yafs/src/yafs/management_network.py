import simpy
import numpy as np
import logging
import pandas as pd
import inspect


class ManagementAgent:
    def __init__(self, 
                 sim, 
                 node_id, 
                 DES_id, 
                 agent_name, 
                 sleep_time, 
                 instructions_per_wakeup, 
                 agent_ipt_percentage,
                 observable_node_ids,
                 metrics_json):
        self.sim = sim
        self.node_id = node_id  # Node where agent is colocated
        self.DES_id = DES_id # Id of the DES process for this agent 
        self.agent_name = agent_name # agent name: agent_name = "agent_" + "node" + str(node_id) + "_" + agent_type.__name__
        self.sleep_time = sleep_time
        self.instructions_per_wakeup = instructions_per_wakeup
        self.message_queue = simpy.Store(self.sim.env)
        self.logger = sim.logger
        self.stop = False
        self.agent_ipt_percentage = agent_ipt_percentage # this percentage is used when updating node metrics to compute the used instructions by both the agent and the module running in the same node_id
        self.observable_node_ids = observable_node_ids

        self.last_time_agent_start_processing = -1 # we should retrieve all agent events that happened [self.last_time_agent_start_processing, end_of_sleeping]
        self.time_of_service = 0 # time spent in previous service

        self.duration_previous_cycle = None
        self.app_filtered_df = None
        self.agent_filtered_df = None
        self.net_filtered_df = None

        self.metrics = {}
        for key, value in metrics_json.items():
            import importlib
            module = importlib.import_module("yafs.management_network")
            cls = getattr(module, value)
            self.metrics[key] = cls(self)

        #call customizable hook
        self.__custom_init__()


 
    def __custom_init__(self):
        #do nothing: to be customized by user for each user new agent
        pass


    def run(self):
        #Registering the DES process into the simulator
        self.sim.des_process_running[self.DES_id] = True
        self.sim.des_control_process[self.agent_name] = self.DES_id

        self.logger.debug("Added_Process - Local Agent Management Algorithm\t#DES:%i" % self.DES_id)
        
        while not self.stop and self.sim.des_process_running[self.DES_id]:
            #Simulated wake up/oeration cycle
            #self.logger.info(f"Agent {self.node_id} waking at {self.sim.env.now}, colocated on node {self.node_id}")
            time_sleep_start = self.sim.env.now
            yield self.sim.env.timeout(self.sleep_time)  # Sleep
            time_sleep_end = self.sim.env.now
            #self.logger.info(f"Agent {self.node_id} executing on node {self.node_id}")

            #Real logic of the management agent
            duration_previous_cycle = self.sleep_time + self.time_of_service
            #print("------------------>duration_previous_cycle:",duration_previous_cycle)
            collected_metrics = self.collect_metrics(duration_previous_cycle) # we pass the time spent in previous cycle so it can compute the metrics
            self.last_time_agent_start_processing = time_sleep_end # update for next iteration
            self.agent_behavior(collected_metrics)   # main method to be customized

            #Compute time working as self.instructions_per_wakeup/float(node["IPT"])  
            att_node = self.sim.topology.G.nodes[self.node_id]
            available_ipt = self.agent_ipt_percentage * float(att_node["IPT"])  #available IPT is divided between colocated agent and app module
            self.time_of_service = self.instructions_per_wakeup / available_ipt  #float(att_node["IPT"])
            
            #Simulate agent' time of service
            yield self.sim.env.timeout(self.time_of_service) # Work 
            time_processing_end = self.sim.env.now           

            #Update agent metrics
            self.sim.metrics.insert_agent_step({
                         "type": self.sim.AGENT_METRIC,
                         "node_id": self.node_id,
                         "DES_id": self.DES_id, 
                         "agent_name": self.agent_name,               
                         "time_sleep_start": time_sleep_start,
                         "time_sleep_end": time_sleep_end,
                         "sleeping_time": float(time_sleep_end-time_sleep_start),
                         "time_processing_end": time_processing_end,
                         "service": float(time_processing_end-time_sleep_end)
                         })

        #self.logger.debug("STOP_Process - Placement Algorithm\t#DES:%i" % self.DES_id)
        

    # custom metrics
    def agent_node_utilization(self):#, df,  duration_previous_cycle):
            
        """
        Returns the service utilization (%) for a list of a observable nodes

        args: agent_filtered_df, duration_previous_cycle
        """

        df = self.agent_filtered_df
        duration_previous_cycle = self.duration_previous_cycle

        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                value = df[df.node_id==id].service.sum()*100/duration_previous_cycle
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })

        return results


    def service_node_utilization(self):#, df, duration_previous_cycle):
        
        """
        Returns the service utilization (%) for a list of a observable nodes

        args: app_filtered_df, duration_previous_cycle
        """

        df = self.app_filtered_df
        duration_previous_cycle = self.duration_previous_cycle

        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                value = df[df["DES.dst"]==id].service.sum()*100/duration_previous_cycle
                value = min(value,100) # in some cases, the "update_metrics function" adds the entry into the DB and still didnt do the last "yield self.env.timeout(service_time)". This needs to be fixed but in the meantime I do this flooring
 
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })

        return results


    def node_average_waiting_time(self):#, df, duration_previous_cycle):
        """
        Return the average waiting time for an input message/request to start being served

        Reminder of relvant data fiels in message event log:
            time_in: time message started being processed by module
            time_out: time message ended being processed by module
            time_emit: time message started to travel the input communication link (opinion from stat code) 
            time_reception: time message enters in module instance queue (same as time_in if queue empty)

        args: app_filtered_df, duration_previous_cycle
        """
        
        df = self.app_filtered_df
        
        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                if df[df["DES.dst"]==id].shape[0] == 0:
                    value = 0
                else:                
                    mean_time_reception = df[df["DES.dst"]==id].time_reception.mean()
                    mean_time_in = df[df["DES.dst"]==id].time_in.mean()
                    value = float(mean_time_in - mean_time_reception)
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })
            
        return results
        
        
    def node_requests_waiting_in(self):

        """
        Returns the number of service requests waiting to be served by the node in each observable node 
        (note: BTB only 1 app service per node, so is the same a sevice~node) 

        args: app_filtered_df
        """

        df = self.app_filtered_df
        
        value = 0
        results = []

        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                df2 = df[df["TOPO.dst"]==id]
                if df2.shape[0] > 0:
                    value = df2.loc[df2['time_out'].idxmax(), 'in_buffer_size_des']
                else:
                    value = 0.0
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
                })
        
        return results
  

    def node_requests_out(self):

        """
        Returns the number of service requests serviced by the node in each observable node since the begining of the simulation
        (note: BTB only 1 app service per node, so is the same a sevice~node) 

        args: app_filtered_df
        """

        df = self.app_filtered_df
        
        value = 0
        results = []

        for id in self.observable_node_ids:
            value = 0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0
            else:
                df2 = df[df["TOPO.dst"]==id]
                value = df2.shape[0]
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
                })
        
        return results


    def net_buffer_size(self):
 
        """
        Returns the most current network buffer size 

        args: net_filtered_df
        """

        df = self.net_filtered_df

        value = 0.0
        if df is None or not isinstance(df, pd.DataFrame):
            value = 0.0
        else:
            value = df.loc[df['ctime'].idxmax(), 'buffer']
        ret ={"metric": inspect.currentframe().f_code.co_name,
              "node_id": self.node_id,
              "value": value
             }
        
        return ret


    def node_nominal_watt(self):

        watt = self.sim.topology.get_info()[0]["WATT"]


    def merge_json_objects(self, *args):
        """
        Merge multiple lists of JSON objects and individual JSON objects into one list.
        
        Args:
            *args: Arbitrary number of lists of dicts or individual dicts.
        
        Returns:
            list: A single flattened list of JSON objects.
        """
        result = []
        for arg in args:
            if isinstance(arg, list):  # if it's a list, extend
                result.extend(arg)
            elif isinstance(arg, dict):  # if it's a dict, append
                result.append(arg)
            else:
                raise TypeError(f"Unsupported type {type(arg)}. Expected dict or list of dicts.")
        return result


    def collect_metrics(self, duration_previous_cycle):
        # metrics = {
        #     "node_utilization": {}, "message_latency": {}, "instructions": {},
        #     "message_count": {}, "agent_execution_time": {}
        # }
        app_event_df = None
        app_filtered_df = None
        agent_filtered_df = None
        net_filtered_df = None
        try:
            app_event_df = self.sim.metrics.get_event_dataframe_where_time_out_gt(metric_type="app", 
                                                                              min_time=self.last_time_agent_start_processing,
                                                                              max_rows=10**6)
            agent_event_df = self.sim.metrics.get_event_dataframe_where_time_out_gt(metric_type="agent", 
                                                                                  min_time=self.last_time_agent_start_processing,
                                                                                  max_rows=10**6)
            
            net_event_df = self.sim.metrics.get_event_dataframe_where_time_out_gt(metric_type="net", 
                                                                                  min_time=self.last_time_agent_start_processing,
                                                                                  max_rows=10**6)
        except IndexError as e:
            print("Error: Entry index is out of bounds.")
        except Exception as e:
            print("Unexpected error:", str(e))
         
        if app_event_df.shape[0] > 0:
            app_event_df['TOPO.dst'] = pd.to_numeric(app_event_df['TOPO.dst'], errors='coerce')
            app_event_df['id'] = pd.to_numeric(app_event_df['id'], errors='coerce')
            self.last_metric_id = int(app_event_df['id'].max()) # updates the top metric id read so far 
            app_filtered_df = app_event_df[app_event_df['TOPO.dst'].isin(self.observable_node_ids)]   # Partial observation defined in elf.observable_node_ids

        if agent_event_df.shape[0] > 0:
            agent_filtered_df = agent_event_df[agent_event_df['node_id'].isin(self.observable_node_ids)]  #Partial observation defined in self.observable_node_ids
       
        if net_event_df.shape[0] > 0:
            net_filtered_df = net_event_df[net_event_df['src'].isin(self.observable_node_ids) |
                                           net_event_df['dst'].isin(self.observable_node_ids) ]  #Partial observation defined in self.observable_node_ids
       
        # updata agent's variables used by Metric object:
        self.duration_previous_cycle = duration_previous_cycle
        self.app_filtered_df = app_filtered_df
        self.agent_filtered_df = agent_filtered_df
        self.net_filtered_df = net_filtered_df

        # Computation of actual metrics delivered to the agent
        service_node_utilization_ret = self.service_node_utilization()
        agent_node_utilization_ret = self.agent_node_utilization()
        net_buffer_size_ret = self.net_buffer_size()
        node_requests_waiting_in_ret = self.node_requests_waiting_in()
        node_requests_out_ret = self.node_requests_out()
        node_average_waiting_time_ret = self.node_average_waiting_time()

        self.node_nominal_watt()



        # Consolidate metric json objects into a single list of json objects
        collected_metrics = self.merge_json_objects(service_node_utilization_ret,
                                                    agent_node_utilization_ret,
                                                    net_buffer_size_ret,
                                                    node_requests_waiting_in_ret,
                                                    node_requests_out_ret,
                                                    node_average_waiting_time_ret) 

        return collected_metrics 
    

    def agent_behavior(self, collected_metric):
        return []



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
            observable_node_ids.append(node_id) # by default, we add the node itself to the list of observable nodes
            observable_node_ids = list(set(observable_node_ids))
            myId = self.sim._Sim__get_id_process()#__get_id_process() is private so I overcome the privatenss explicitly (not nice)
            agent_name = "agent_" + "node" + str(node_id) + "_" + agent_type.__name__
            metrics_json = agent_json["metrics"]

            #make sure agent_ipt_percentage is within range [0,1]. If not floor it between [0,1] + log a warning
            agent_ipt_percentage_01 = max(0, min(1, agent_ipt_percentage))

            #observable_node_ids = agent_json["observable_node_ids"]
            agent = agent_type(self.sim, node_id, myId, agent_name, sleep_time, instructions_per_wakeup, 
                               agent_ipt_percentage_01, observable_node_ids, metrics_json)
            self.agents[node_id] = agent
            # start gant process        

            self.sim.env.process(agent.run())
            # Note: agent registration, logging and metrics saving is done in the agent run() method in each iteration wake up 

            """
            DES-process who controls the invocation of a management agent
            """
            self.sim.des_process_running[myId] = True
            self.sim.des_control_process[agent_name] = myId                                               


    def run(self,sim):
        """
        This method will be invoked during the simulation to change the assignment of the management agents to the topology

        Args:
            sim (:mod: yafs.core.Sim)
        """
        self.logger.debug("Activiting - RUN - ManagementAgentnetwork")


# Metric classes

class Metric:
    
    def __init__(self):
        self.agent = None

class ServiceNodeUtilization(Metric):

    def __init__(self, agent):
        self.agent = agent

    
    def __call__(self):
        
        """
        Returns the service utilization (%) for a list of a observable nodes
        """

        df = self.app_filtered_df
        duration_previous_cycle = self.duration_previous_cycle

        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                value = df[df["DES.dst"]==id].service.sum()*100/duration_previous_cycle
                value = min(value,100) # in some cases, the "update_metrics function" adds the entry into the DB and still didnt do the last "yield self.env.timeout(service_time)". This needs to be fixed but in the meantime I do this flooring
 
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })

        return results
    

class AgentNodeUtilization(Metric):

    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):
            
        """
        Returns the service utilization (%) for a list of a observable nodes

        args: agent_filtered_df, duration_previous_cycle
        """

        df = self.agent_filtered_df
        duration_previous_cycle = self.duration_previous_cycle

        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                value = df[df.node_id==id].service.sum()*100/duration_previous_cycle
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })

        return results

class NodeAverageWaitingTime(Metric):

    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):
        """
        Return the average waiting time for an input message/request to start being served

        Reminder of relvant data fiels in message event log:
            time_in: time message started being processed by module
            time_out: time message ended being processed by module
            time_emit: time message started to travel the input communication link (opinion from stat code) 
            time_reception: time message enters in module instance queue (same as time_in if queue empty)

        args: app_filtered_df, duration_previous_cycle
        """
        
        df = self.app_filtered_df
        
        results = []
        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                if df[df["DES.dst"]==id].shape[0] == 0:
                    value = 0
                else:                
                    mean_time_reception = df[df["DES.dst"]==id].time_reception.mean()
                    mean_time_in = df[df["DES.dst"]==id].time_in.mean()
                    value = float(mean_time_in - mean_time_reception)
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
            })
            
        return results
        

class NodeRequestsWaitingIn(Metric):

    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):

        """
        Returns the number of service requests waiting to be served by the node in each observable node 
        (note: BTB only 1 app service per node, so is the same a sevice~node) 

        args: app_filtered_df
        """

        df = self.app_filtered_df
        
        value = 0
        results = []

        for id in self.observable_node_ids:
            value = 0.0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0.0
            else:
                df2 = df[df["TOPO.dst"]==id]
                if df2.shape[0] > 0:
                    value = df2.loc[df2['time_out'].idxmax(), 'in_buffer_size_des']
                else:
                    value = 0.0
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
                })
        
        return results       


class NodeRequestsOut(Metric):

    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):
        """
        Returns the number of service requests serviced by the node in each observable node since the begining of the simulation
        (note: BTB only 1 app service per node, so is the same a sevice~node) 

        args: app_filtered_df
        """

        df = self.app_filtered_df
        
        value = 0
        results = []

        for id in self.observable_node_ids:
            value = 0
            if df is None or not isinstance(df, pd.DataFrame):
                value = 0
            else:
                df2 = df[df["TOPO.dst"]==id]
                value = df2.shape[0]
            results.append({
                "metric": inspect.currentframe().f_code.co_name,
                "node_id": id,
                "value": value
                })
        
        return results


class NetBufferSize(Metric):

    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):
        """
        Returns the most current network buffer size 

        args: net_filtered_df
        """

        df = self.net_filtered_df

        value = 0.0
        if df is None or not isinstance(df, pd.DataFrame):
            value = 0.0
        else:
            value = df.loc[df['ctime'].idxmax(), 'buffer']
        ret ={"metric": inspect.currentframe().f_code.co_name,
              "node_id": self.node_id,
              "value": value
             }
        
        return ret


class NodeNominalWatt(Metric):
    
    def __init__(self, agent):
        self.agent = agent
    
    def __call__(self):
        watt = self.sim.topology.get_info()[0]["WATT"]


# Intervention Classes

class Intervention:

    def __init__(self):
        print("DiscreteIntervention to be revised maybe irrelevant")

    def f():
        print(2)

class DiscretePercentileInterventions(Intervention):
    def __init__(self, agent, sim, des_id, pctls):
        """
        Args:
            sim: core simulator with access to intervention vector "sim.des_pct_instructions"
            des_id. discrete event simulator process id representing the service running in node_id
            pctls: vector of monotonically increasing percentiles (in [0,1]) representing the percentage 
                   of the service/message instructions to be executed in each call. This value is multiplied 
                   by the message instructions value, then the QoS function is use to recover the obtained QoS 
                   to execute this service with the corresponding instructions  
        """
           
        self.agent = agent
        self.sim = sim
        self.des_id = des_id

        if not pctls:
            raise ValueError("pctls list is empty")
        for i, p in enumerate(pctls):
            if not (0.0 <= p <= 1.0):
                raise ValueError(f"Percentile {p} at index {i} is not in [0,1]")
            if i > 0 and p < pctls[i-1]:
                raise ValueError(f"Percentiles not monotonically increasing at index {i}: {p} < {pctls[i-1]}")
        self.pctls = pctls

    def __call__(self, action_id, service_des_id):
        """
        applies intervention
        Args:
            action_id: position in list self.pctls 
        """
        if not isinstance(action_id, int):
            raise TypeError(f"Parameter action_id must be int, but got {type(x).__name__}")
        if action_id >= len(self.pctls):
            raise ValueError(f"Parameter action_id must be less than {len(self.pctls)}, but got {action_id}")
    
        des_pct_instructions_old = self.sim.des_pct_instructions[service_des_id]
        node_id = self.sim.alloc_DES[service_des_id]

        # Perform intervention
        self.sim.des_pct_instructions[service_des_id] = self.pctls[action_id]

        # Perform insert intro into action event data base
        self.sim.metrics.insert_action(
            {"action_class_type": self.__class__.__name__,
             "agent_class_type": self.agent.__class__.__name__, 
             "action_id": action_id, 
             "node_id": node_id,
             "agent_des_id": self.des_id,
             "service_des_id":service_des_id,
             "time_intervention": self.sim.env.now,
             "log": None
             })


