"""Trip orchestrator: the LangGraph agent that turns a request into a proposal.

The only module that calls an LLM. It proposes; it never moves money or books anything itself. To act it calls
``app.modules.booking``'s public functions. It must not import ``app.modules.payment``.
"""
