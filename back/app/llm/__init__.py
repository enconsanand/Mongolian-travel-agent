"""Model gateway: code asks for a capability (``intent.extract``), config picks provider and model; with fallback,
schema validation, PII redaction and cost metering. Only ``app.modules.orchestrator`` may import this.
"""
