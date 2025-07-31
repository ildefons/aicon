import csv

class Metrics:

    TIME_LATENCY = "time_latency"
    TIME_WAIT =  "time_wait"
    TIME_RESPONSE = "time_response"
    TIME_SERVICE = "time_service"
    TIME_TOTAL_RESPONSE = "time_total_response"

    WATT_SERVICE = "byService"
    WATT_UPTIME = "byUptime"


    def __init__(self, default_results_path=None):
        columns_event = ["id","type", "app", "module", "message","DES.src","DES.dst","TOPO.src","TOPO.dst","module.src","service", "time_in","time_out",
                         "time_emit","time_reception"]
        columns_link = ["id","type", "src", "dst", "app", "latency", "message", "ctime", "size","buffer"]
        #ILDE: columns of agent trace CSV file
        columns_agent = ["type", "node_id","DES_id","agent_name","time_sleep_start","time_sleep_end","sleeping_time","time_processing_end", "service"]

        path = "result"
        if  default_results_path is not None:
            path = default_results_path

        self.__filef = open("%s.csv" % path, "w")
        self.__filel = open("%s_link.csv"%path, "w")
        #ILDE
        self.__filea = open("%s_agent.csv"%path, "w")

        self.__ff = csv.writer(self.__filef)
        self.__ff_link = csv.writer(self.__filel)
        #ILDE
        self.__ff_agent = csv.writer(self.__filea)
        self.__ff.writerow(columns_event)
        self.__ff_link.writerow(columns_link)
        #ILDE
        self.__ff_agent.writerow(columns_agent)


    def flush(self):
        self.__filef.flush()
        self.__filel.flush()
        #ILDE
        self.__filea.flush()

    def insert(self,value):

        self.__ff.writerow([value["id"],value["type"],
                    value["app"],
                    value["module"],
                    value["message"],
                    value["DES.src"],
                    value["DES.dst"],
                    value["TOPO.src"],
                    value["TOPO.dst"],
                    value["module.src"],
                    value["service"],
                    value["time_in"],
                    value["time_out"],
                    value["time_emit"],
                    value["time_reception"]
                            ])

    def insert_link(self, value):
        self.__ff_link.writerow([value["id"],value["type"],
                    value["src"],
                    value["dst"],
                    value["app"],
                    value["latency"],
                    value["message"],
                    value["ctime"],
                    value["size"],
                    value["buffer"],

                            ])

    #ILDE: metrics event from a management agant step
    def insert_agent_step(self, value):
        self.__ff_agent.writerow([
                    value["type"],
                    value["node_id"],
                    value["DES_id"], 
                    value["agent_name"],
                    value["time_sleep_start"],
                    value["time_sleep_end"],
                    value["sleeping_time"],
                    value["time_processing_end"],
                    value["service"]
                            ])


    def close(self):
        self.__filef.close()
        self.__filel.close()
        #ILDE
        self.__filea.close()
