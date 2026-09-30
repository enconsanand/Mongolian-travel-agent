"""Separate processes started from the same image: MCP server, A2A agents (lodging, payment), QPay simulator.

They talk to the core over their protocol (MCP, A2A, HTTP) and must not import ``app.modules``.
"""
