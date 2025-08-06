import csv
import io  #new

class Metrics_online:
    TIME_LATENCY = "time_latency"
    TIME_WAIT = "time_wait"
    TIME_RESPONSE = "time_response"
    TIME_SERVICE = "time_service"
    TIME_TOTAL_RESPONSE = "time_total_response"

    WATT_SERVICE = "byService"
    WATT_UPTIME = "byUptime"

    def __init__(self, default_results_path=None):
        self._bufferf = io.StringIO()  #new
        self._bufferl = io.StringIO()  #new
        self._buffera = io.StringIO()  #new

        self.__ff = csv.writer(self._bufferf)  #new
        self.__ff_link = csv.writer(self._bufferl)  #new
        self.__ff_agent = csv.writer(self._buffera)  #new

        self._event_columns = [  #new
            "id","type", "app", "module", "message",
            "DES.src","DES.dst","TOPO.src","TOPO.dst",
            "module.src","service", "time_in","time_out",
            "time_emit","time_reception"
        ]
        self._link_columns = [  #new
            "id","type", "src", "dst", "app", "latency",
            "message", "ctime", "size","buffer"
        ]
        self._agent_columns = [  #new
            "type", "node_id","DES_id","agent_name",
            "time_sleep_start","time_sleep_end",
            "sleeping_time","time_processing_end", "service"
        ]

        self.__ff.writerow(self._event_columns)  #new
        self.__ff_link.writerow(self._link_columns)  #new
        self.__ff_agent.writerow(self._agent_columns)  #new

    def insert(self, value):
        self.__ff.writerow([  #new
            value["id"], value["type"], value["app"], value["module"],
            value["message"], value["DES.src"], value["DES.dst"],
            value["TOPO.src"], value["TOPO.dst"], value["module.src"],
            value["service"], value["time_in"], value["time_out"],
            value["time_emit"], value["time_reception"]
        ])

    def insert_link(self, value):
        self.__ff_link.writerow([  #new
            value["id"], value["type"], value["src"], value["dst"],
            value["app"], value["latency"], value["message"],
            value["ctime"], value["size"], value["buffer"]
        ])

    def insert_agent_step(self, value):
        self.__ff_agent.writerow([  #new
            value["type"], value["node_id"], value["DES_id"],
            value["agent_name"], value["time_sleep_start"],
            value["time_sleep_end"], value["sleeping_time"],
            value["time_processing_end"], value["service"]
        ])

    def get_event_csv_content(self):  #new
        self._bufferf.seek(0)  #new
        return self._bufferf.read()  #new

    def get_link_csv_content(self):  #new
        self._bufferl.seek(0)  #new
        return self._bufferl.read()  #new

    def get_agent_csv_content(self):  #new
        self._buffera.seek(0)  #new
        return self._buffera.read()  #new

    def save_to_file(self, path="result"):  #new
        with open(f"{path}.csv", "w") as f:  #new
            f.write(self.get_event_csv_content())  #new
        with open(f"{path}_link.csv", "w") as f:  #new
            f.write(self.get_link_csv_content())  #new
        with open(f"{path}_agent.csv", "w") as f:  #new
            f.write(self.get_agent_csv_content())  #new

    def _get_last_n_rows(self, buffer, n):  #new
        buffer.seek(0)  #new
        reader = csv.DictReader(buffer)  #new
        rows = list(reader)  #new
        return rows[-n:] if len(rows) >= n else rows  #new

    def get_last_event_type(self, entry_index):  #new
        rows = self._get_last_n_rows(self._bufferf, 100)  #new
        if 0 < entry_index <= len(rows):  #new
            return rows[entry_index - 1]["type"]  #new
        raise IndexError("Entry index out of bounds")  #new

    def get_last_link_type(self, entry_index):  #new
        rows = self._get_last_n_rows(self._bufferl, 100)  #new
        if 0 < entry_index <= len(rows):  #new
            return rows[entry_index - 1]["type"]  #new
        raise IndexError("Entry index out of bounds")  #new

    def get_last_agent_type(self, entry_index):  #new
        rows = self._get_last_n_rows(self._buffera, 100)  #new
        if 0 < entry_index <= len(rows):  #new
            return rows[entry_index - 1]["type"]  #new
        raise IndexError("Entry index out of bounds")  #new

    # Get n rows starting from row m (0-based) #new
    def _get_since_row_m_n_rows(self, buffer, m, n):  #new
        buffer.seek(0)  #new
        reader = csv.DictReader(buffer)  #new
        rows = list(reader)  #new
        if m < 0 or m >= len(rows):  #new
            raise IndexError("Start index m is out of bounds")  #new
        return rows[m : m + n]  #new
    
    def flush(self):  #new: NOT NECESSARY
        self._bufferf.flush()  #new
        self._bufferl.flush()  #new
        self._buffera.flush()  #new

    def close(self):  #new: NOT NECESSARY
        self._bufferf.close()  #new
        self._bufferl.close()  #new
        self._buffera.close()  #new
