import csv
import io
import pandas as pd  # for dataframe support

class Metrics_online:
    TIME_LATENCY = "time_latency"
    TIME_WAIT = "time_wait"
    TIME_RESPONSE = "time_response"
    TIME_SERVICE = "time_service"
    TIME_TOTAL_RESPONSE = "time_total_response"

    WATT_SERVICE = "byService"
    WATT_UPTIME = "byUptime"

    def __init__(self, default_results_path=None):
        # In-memory buffers instead of files
        self._bufferf = io.StringIO()
        self._bufferl = io.StringIO()
        self._buffera = io.StringIO()

        self.__ff = csv.writer(self._bufferf)
        self.__ff_link = csv.writer(self._bufferl)
        self.__ff_agent = csv.writer(self._buffera)

        # Column headers
        self._event_columns = [
            "id","type", "app", "module", "message",
            "DES.src","DES.dst","TOPO.src","TOPO.dst",
            "module.src","service", "time_in","time_out",
            "time_emit","time_reception"
        ]
        self._link_columns = [
            "id","type", "src", "dst", "app", "latency",
            "message", "ctime", "size","buffer"
        ]
        self._agent_columns = [
            "type", "node_id","DES_id","agent_name",
            "time_sleep_start","time_sleep_end",
            "sleeping_time","time_processing_end", "service"
        ]

        # Write headers
        self.__ff.writerow(self._event_columns)
        self.__ff_link.writerow(self._link_columns)
        self.__ff_agent.writerow(self._agent_columns)

    # Insertion Methods
    def insert(self, value):
        self.__ff.writerow([
            value["id"], value["type"], value["app"], value["module"],
            value["message"], value["DES.src"], value["DES.dst"],
            value["TOPO.src"], value["TOPO.dst"], value["module.src"],
            value["service"], value["time_in"], value["time_out"],
            value["time_emit"], value["time_reception"]
        ])

    def insert_link(self, value):
        self.__ff_link.writerow([
            value["id"], value["type"], value["src"], value["dst"],
            value["app"], value["latency"], value["message"],
            value["ctime"], value["size"], value["buffer"]
        ])

    def insert_agent_step(self, value):
        self.__ff_agent.writerow([
            value["type"], value["node_id"], value["DES_id"],
            value["agent_name"], value["time_sleep_start"],
            value["time_sleep_end"], value["sleeping_time"],
            value["time_processing_end"], value["service"]
        ])

    # Get full CSV contents
    def get_event_csv_content(self):
        self._bufferf.seek(0)
        return self._bufferf.read()

    def get_link_csv_content(self):
        self._bufferl.seek(0)
        return self._bufferl.read()

    def get_agent_csv_content(self):
        self._buffera.seek(0)
        return self._buffera.read()

    # Save CSV contents to file
    def save_to_file(self, path="result"):
        with open(f"{path}.csv", "w") as f:
            f.write(self.get_event_csv_content())
        with open(f"{path}_link.csv", "w") as f:
            f.write(self.get_link_csv_content())
        with open(f"{path}_agent.csv", "w") as f:
            f.write(self.get_agent_csv_content())

    # Get last N rows from a buffer
    def _get_last_n_rows(self, buffer, n):
        buffer.seek(0)
        reader = csv.DictReader(buffer)
        rows = list(reader)
        return rows[-n:] if len(rows) >= n else rows

    # Get N rows starting from row M
    def _get_since_row_m_n_rows(self, buffer, m, n):
        buffer.seek(0)
        reader = csv.DictReader(buffer)
        rows = list(reader)
        if m < 0 or m >= len(rows):
            raise IndexError("Start index m is out of bounds")
        return rows[m : m + n]

    # Get "type" field from absolute row index
    def get_event_type_at_row(self, index):
        df = self.get_event_dataframe_since(index, max_rows=1)
        if not df.empty:
            return df.iloc[0]["type"]
        raise IndexError("Index out of bounds")

    # Get DataFrame of events from row N (default up to 1000 rows)
    def get_event_dataframe_since(self, type, start_index, max_rows=1000):
        rows = None
        if type == "app":
            rows = self._get_since_row_m_n_rows(self._bufferf, start_index, max_rows)
        elif type == "agent":
            rows = self._get_since_row_m_n_rows(self._buffera, start_index, max_rows)
        return pd.DataFrame(rows)

    def get_event_dataframe_where_time_out_gt(self, metric_type, time_th_ok, max_rows=1000):
        try:
            if type == "app":
                mybuffer = self._bufferf
                mybuffer.seek(0)
                df = pd.read_csv(mybuffer)
                df_filtered = df[pd.to_numeric(df["time_in"], errors="coerce") > time_th_ok]
                return df_filtered.head(max_rows)
            elif type == "agent":
                mybuffer = self._buffera
                mybuffer.seek(0)
                df = pd.read_csv(mybuffer)
                df_filtered = df[pd.to_numeric(df["time_sleep_end"], errors="coerce") > time_th_ok]
                return df_filtered.head(max_rows)
            else: 
                raise Exception("Unknown metric type:", metric_type)
        except Exception as e:
            print("Error reading buffer as DataFrame:", e)
            return pd.DataFrame()


    # Optional flush/close for cleanup (not strictly needed)
    def flush(self):
        self._bufferf.flush()
        self._bufferl.flush()
        self._buffera.flush()

    def close(self):
        self._bufferf.close()
        self._bufferl.close()
        self._buffera.close()
