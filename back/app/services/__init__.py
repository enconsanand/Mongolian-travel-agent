"""Separate processes started from the same image (currently the QPay simulator).

They talk to the core over HTTP and must not import ``app.modules``.
"""
