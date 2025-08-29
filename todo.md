# Development agenda

(*) focuss points

- Add metrics:
    - (*)Average time to start being served

- (*) Add cost model (not yet used in lab papers)
    - do research on cost models that can be simulaed (model has to be "citable")
    - take a look initial surveys:
        - https://x.com/i/grok/share/3czCDcxYWqGep9Uxf8Kpm8NFt
        - https://chatgpt.com/share/68b057c0-de04-8013-b8dd-5011dd7bd3f2
    - it makes node "IPT" and message "instructions" actionable variables
    - It may integrate both device usage and energy consumption into an integrated or seprated metrics

- Actions for redirecting incoming messages to other instances of the same service (e.g. used in onloading electric vehicles)
    - Possibility: 
        - Agents look for same process instances in nodes from observability list
        - Agents keep "message forwarding probability vector" that defines where to foward incoming messages (can be keeping it for processing itself)
        - Update message destination accordingly and push message again to the "network_ctrl_pipe" (if different from itself)
        - Agent can make interventions into the "message forwarding probability vector" to simulate "onloading"
        - Note: this mechanism is interesting to explore decentralized algorithms for resource optimization.

- (*) Actions for deploy/undeploy services on observable nodes (e.g. used in streaming application). 
    - It can serve as alternative to "redirecting incoming messages" if the central routing algorithm can redirect messages to nodes with lower demand.

- (*) Consolidate json metrics objects into a single json metric object and make "collect_metrics" to return it  

- (*) Consolidate ManagementAgent run method: cosider merging get_management_actions and apply_actions into 1 method

- How can I make metric collection more efficient:
    - Problem: agents wake up at different rates so is hard to simply colllect once for all
    - Possibility: have a single simpy process that wakesup every T times units and computes all possible new metrics and pushesthem to a simpy store.   

- Elaborated examples:
    - Simple examples for custom agents: read metrics, do interventions, define observability set, define QoS class, and so on
    - Depending of implemented interventions: EV case, stream app, federated learning 