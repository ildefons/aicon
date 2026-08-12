# -*- coding: utf-8 -*-
import random

import math

import copy
from numbers import Number

# ILDE: QoS related code
class LinearQoS:
    def __init__(self, L: float, R: float): # R_inst is the number of instructions corresponding to R
                                                                  # L, R: in [0,1]
        if L >= R:
            raise ValueError("L must be strictly less than R.")
        self.L = L
        self.R = R

        # define the clamped linear function
        def linear_clamped(x):  # Input x: is in [0,1] where 0 is o% of nominal instructions, and 1 is 100% of nominal instructions 
            if x <= self.L:
                return 0.0
            elif x >= self.R:
                return 1.0
            else:
                return 1.0 * (x - self.L) / (self.R - self.L)

        self.f = linear_clamped   # store as attribute

    def __call__(self, x: float) -> float:
        """Optionally make QoS callable directly"""
        return self.f(x)
    

class SaturatingExpQoS:
    def __init__(self, Q_max: float, a: float):
        """
        Saturating exponential QoS model (CPU-only):
            Q(x) = Q_max * (1 - exp(-a * x))

        Args:
            Q_max (float): Maximum achievable QoS (e.g., 100.0).
            a (float): Sensitivity parameter (must be positiv
            - If beta=0 → only saturation (no decline).
            - If beta>0 → possible decline at high x.

        Example:
            Q_max = 100
            alpha = 0.02
            beta = 0.001
            R_inst = 1000e).

        Notes:
            a must be strictly positive
            Small a: very slow growth.
            Needs a lot of CPU before QoS approaches its maximum.
            Large a: very fast growth.
            Even a small amount of CPU quickly yields near-max QoS.

        How to compute a:
            If my service/message takes by default 1000 instructions to execute "fully" (Qmax)
            and I want QoS(500) = 0.5*Qmax
            a = ln(2)/500
            , with this a, QoS(1000) = 75

            If my service/message takes by default 1000 instructions to execute "fully" (Qmax)
            and I want QoS(100) = 0.8*Qmax
            a = ln(5)/100 = 0.01609438
            , with this a, QoS(1000) = 99.999999999

        """
        if Q_max <= 0:
            raise ValueError("Q_max must be positive.")
        if a <= 0:
            raise ValueError("Parameter a must be positive.")

        self.Q_max = Q_max
        self.a = a

        def f(x: float) -> float:  # Input x: is in [0,1] where 0 is o% of nominal instructions, and 1 is 100% of nominal instructions 
            if x < 0:
                raise ValueError("CPU quota x must be nonnegative.")
            return self.Q_max * (1.0 - math.exp(-self.a * x))
        
        def __call__(self, x: float) -> float:
            """Optionally make QoS callable directly"""
            return self.f(x)

class USLQoS:
    def __init__(self, Q_max: float, alpha: float, beta: float, R_inst: float):
        """
        Universal Scalability Law (USL) QoS model with normalized input:
            Q(x) = Q_max * [ N / (1 + alpha*(N-1) + beta*N*(N-1)) ]

        Citations:
            1)chatgpt discussion: https://chatgpt.com/share/68b55c9e-42c8-8013-8106-e008ab350f23
            
            2)Khan, Hassan Mahmood, Fang-Fang Chua, and Timothy Tzen Vun Yap. 
            "ReSQoV: a scalable resource allocation model for qos-satisfied cloud services." 
            Future Internet 14.5 (2022): 131.

        Args:
            Q_max (float): Maximum achievable QoS (normalization factor).
            alpha (float): Contention coefficient (>= 0).
            beta (float): Coherency coefficient (>= 0).
            R_inst (float): Nominal number of instructions required for full QoS.
                            This sets the scale for normalization.

        Notes:
            - Input x must be in [0,1], representing the fraction of R_inst.
              Example: x=0.5 means half the nominal instructions.
            - Internally, we map x → N = 1 + (x * (R_inst - 1)).
              So at x=0 → N=1 (minimum unit).
              At x=1 → N=R_inst (full resources).
            - If beta=0 → only saturation (no decline).
            - If beta>0 → possible decline at high x.

        Example:
            Q_max = 100
            alpha = 0.02
            beta = 0.001
            R_inst = 1000

            model = USLQoS(Q_max, alpha, beta, R_inst)
            qos_half = model(0.5)   # QoS at 50% of nominal instructions
        """
        if Q_max <= 0:
            raise ValueError("Q_max must be positive.")
        if alpha < 0 or beta < 0:
            raise ValueError("alpha and beta must be nonnegative.")
        if R_inst <= 1:
            raise ValueError("R_inst must be > 1.")

        self.Q_max = Q_max
        self.alpha = alpha
        self.beta = beta
        self.R_inst = R_inst

        def f(x: float) -> float:
            if not (0 <= x <= 1):
                raise ValueError("x must be in [0,1].")
            # Map normalized x to equivalent 'processors' N
            N = 1 + x * (self.R_inst - 1)  #Note: it scales in [1,Rinst] instead of [0,Rinst]
            # N = x * self.R_inst #Note: it scales in [0,Rinst] but not good
            # Reason: https://x.com/i/grok/share/6giqTLUc9Mlfeq51bopPKmdUM
            # Reason. it prevents unwanted behavior at N = 0 (where N = x*R_inst)
            
            denom = 1.0 + self.alpha * (N - 1) + self.beta * N * (N - 1)
            return self.Q_max * (N / denom)

        self.f = f

    def __call__(self, x: float) -> float:
        return self.f(x)
    

#ILDE: Other QoS could be more appropiate depending of the algorithm being modelled:
# For many modern algorithms, the relationship is highly non-linear. Here are common cases where the linear model fails:

# 1) Diminishing Returns (Logarithmic/Exponential Decay): This is perhaps the most common pattern. 

# 2) Huge quality gains happen in the first few iterations, and then each subsequent iteration provides less and less improvement.
# Example: Most machine learning training and inference. The loss drops very quickly at first and then plateaus.
# Model: A logarithmic model (QoS = a * log(iterations) + b) is often a better fit.

# 3) "Aha!" Moments (Step Function): The quality might remain near zero for many iterations and then suddenly jump to a high value when the algorithm finds a good solution or converges.
# Example: Some combinatorial optimization algorithms (e.g., genetic algorithms, constraint solvers). They search and search until they suddenly find a valid, high-quality solution.
# Model: A step function or a very steep sigmoid function.

# 4) Sigmoid / S-Curve: A combination of the above. Slow initial progress, then a period of rapid, near-linear improvement, followed by a plateau with diminishing returns. This is a very common pattern.
# Model: A sigmoid function qos=LinearQoS()like QoS = 100 / (1 + e^(-k*(iterations - M))) where M is the midpoint and k controls the steepness.

# 5) Unpredictable / Noisy Progress: The quality might oscillate, go down before it goes up, or be stochastic.
# Example: Training a neural network with stochastic gradient descent. The loss curve is famously bumpy.
# Model: Very hard to model precisely. Often requires probabilistic or worst-case modeling.


class Message:
    """
    A message is set by the following values:

    Args:
        name (str): a name, unique for each application

        src (str): the name of module who send this message

        dst (dst): the nsame of module who receive this message

        inst (int): the number of instructions to be executed ((by default 0), Instead of MIPS, we use IPt since the time is relative to the simulation units.

        bytes (int): the size in bytes (by default 0)

    Internal args used in the **yafs.core** are:
        timestamp (float): simulation time. Instant of time that was created.

        path (list): a list of entities of the topology that has to travel to reach its target module from its source module.

        dst_int (int): an identifier of the intermediate entity in which it is in the process of transmission.

        app_name (str): the name of the application
    """

    def __init__(self, name, src, dst, instructions=0, bytes=0,broadcasting=False, qos = None): # ILDE: I added qos so I can monitor/control QoS aaf of instructions (default)
        self.name = name
        self.src = src
        self.dst = dst

        #BEGINILDE (PRAISE)
        #self.inst = instructions
        self.instructions = instructions
        if isinstance(instructions, Number):
            self.inst = instructions
        else:
            self.inst = None
        #ENDILDE (PRAISE)

        self.bytes = bytes

        self.timestamp = 0
        self.path = []
        self.dst_int = -1
        self.app_name = None
        self.timestamp_rec = 0

        self.idDES = None
        self.broadcasting = broadcasting
        self.last_idDes = []
        self.id = -1

        self.original_DES_src = None #This attribute identifies the user when multiple users are in the same node

        #ILDE: QoS related code
        self.qos = qos            

    def __str__(self):
        print  ("{--")
        print (" Name: %s (%s)" %(self.name,self.id))
        print (" From (src): %s  to (dst): %s" %(self.src,self.dst))
        print (" --}")
        return ("")

    # BEGINILDE(PRAISE): necessary to allow "instructions" to be a distribution
    def instantiate(self):
        msg = copy.copy(self)

        if isinstance(self.instructions, Number):
            msg.inst = self.instructions
        else:
            msg.inst = self.instructions.next()

        return msg
    # ENDILDE(PRAISE)

def fractional_selectivity(threshold):
    return random.random() <= threshold


def create_applications_from_json(data):
    applications = {}
    for app in data:
        a = Application(name=app["name"])
        modules = [{"None": {"Type": Application.TYPE_SOURCE}}]
        for module in app["module"]:
            modules.append({module["name"]: {"RAM": module["RAM"], "Type": Application.TYPE_MODULE}})
        a.set_modules(modules)

        ms = {}
        for message in app["message"]:
            # print "Creando mensaje: %s" %message["name"]
            ms[message["name"]] = Message(message["name"], message["s"], message["d"],
                                          instructions=message["instructions"], bytes=message["bytes"])
            if message["s"] == "None":
                a.add_source_messages(ms[message["name"]])

        # print "Total mensajes creados %i" %len(ms.keys())
        for idx, message in enumerate(app["transmission"]):
            if "message_out" in message.keys():
                a.add_service_module(message["module"], ms[message["message_in"]], ms[message["message_out"]],
                                     fractional_selectivity, threshold=1.0)
            else:
                a.add_service_module(message["module"], ms[message["message_in"]])

        applications[app["name"]] = a

    return applications


class Application:
    """
    An application is defined by a DAG between modules that generate, compute and receive messages.

    Args:
        name (str): The name must be unique within the same topology.

    Returns:
        an application

    """
    TYPE_SOURCE = "SOURCE"  # "SENSOR"
    "A source is like sensor"

    TYPE_MODULE = "MODULE"
    "A module"

    TYPE_SINK = "SINK"
    "A sink is like actuator"

    def __init__(self, name):
        self.name = name
        self.services = {}
        self.messages = {}
        self.modules = []
        self.modules_src = []
        self.modules_sink = []
        self.modules_sink_ilde = [] # the previous "modules_sink" only store the last sing to be declared. Here we keep all of them
        self.data = {}

    def __str__(self):
        print ("___ APP. Name: %s" % self.name)
        print (" __ Transmissions ")
        for m in self.messages.values():
            print ("\tModule: None : M_In: %s  -> M_Out: %s " %(m.src,m.dst))

        for modulename in self.services.keys():
            m = self.services[modulename]
            print ("\t",modulename)
            for ser in m:
                if "message_in" in ser.keys():
                    try:
                            print ("\t\t M_In: %s  -> M_Out: %s " % (ser["message_in"].name, ser["message_out"].name))
                    except:
                            print ("\t\t M_In: %s  -> M_Out: [NOTHING] " % (ser["message_in"].name))
        return ""

    def set_modules(self,data):
        """
        Pure source or sink modules must be typified

        Args:
            data (dict) : a set of characteristic of modules
        """
        for module in data:
            name = list(module.keys())[0]
            type = list(module.values())[0]["Type"]
            if type == self.TYPE_SOURCE:
                self.modules_src.append(name)
            elif type == self.TYPE_SINK:
                self.modules_sink = name
            
            #ILDE
            if type == self.TYPE_SINK:
                self.modules_sink_ilde.append(name)
            

            self.modules.append(name)

        self.data = data

        # self.modules_sink = modules
    # def set_module(self, modules, type_module):
    #     """
    #     Pure source or sink modules must be typified
    #
    #     Args:
    #         modules (list): a list of modules names
    #         type_module (str): TYPE_Smodules_sinkOURCE or TYPE_SINK
    #     """
    #     if type_module == self.TYPE_SOURCE:
    #         self.modules_src = modules
    #     elif type_module == self.TYPE_SINK:
    #         self.modules_sink = modules
    #     elif type_module == self.TYPE_MODULE:
    #         self.modules_pure = modules

    def get_pure_modules(self):
        """
        Returns:
            a list of pure source and sink modules
        """
        return [s for s in self.modules if s not in self.modules_src and s not in self.modules_sink]
    
    def get_pure_modules_ilde(self):
        """
        Returns:
            a list of pure source and sink modules
        """
        return [s for s in self.modules if s not in self.modules_src and s not in self.modules_sink_ilde]

    def get_sink_modules(self):
        """
        Returns:
            a list of sink modules
        """
        return self.modules_sink
    
    def get_sink_modules_ilde(self):
        """
        Returns:
            a list of sink modules (ILDE: all of them)
        """
        return self.modules_sink_ilde

    def add_source_messages(self, msg):
        """
        Add in the application those messages that come from pure sources (sensors). This distinction allows them to be controlled by the (:mod:`Population`) algorithm
        """
        self.messages[msg.name] = msg


    def get_message(self,name):
        """
        Returns: a message instance from the identifier name
        """
        return self.messages[name]

    """
    ADD SERVICE
    """

    def add_service_source(self, module_name, distribution=None, message=None, module_dest=[], p=[]):
        """
        Link to each non-pure module a management for creating messages

        Args:
            module_name (str): module name

            distribution (function): a function with a distribution function

            message (Message): the message

            module_dest (list): a list of modules who can receive this message. Broadcasting.

            p (list): a list of probabilities to send this message. Broadcasting

        Kwargs:
            param_distribution (dict): the parameters for *distribution* function

        """
        if distribution is not None:
            if module_name not in self.services:
                self.services[module_name] = []
            self.services[module_name].append(
                {"type": Application.TYPE_SOURCE, "dist": distribution,
                 "message_out": message, "module_dest": module_dest, "p": p})

    def add_service_module(self, module_name, message_in, message_out="", distribution="", module_dest=[], p=[],
                           **param):

        """
        Link to each non-pure module a management of transfering of messages

        Args:
            module_name (str): module name

            message_in (Message): input message

            message_out (Message): output message. If Empty the module is a sink

            distribution (function): a function with a distribution function

            module_dest (list): a list of modules who can receive this message. Broadcasting.

            p (list): a list of probabilities to send this message. Broadcasting

        Kwargs:
            param (dict): the parameters for *distribution* function

        """
        if not module_name in self.services:
            self.services[module_name] = []

        self.services[module_name].append({"type": Application.TYPE_MODULE, "dist": distribution, "param": param,
                                           "message_in": message_in, "message_out": message_out,
                                           "module_dest": module_dest, "p": p})
