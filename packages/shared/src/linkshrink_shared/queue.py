"""Redis Streams helpers and the click-event payload contract.

XADD/XREADGROUP/XACK/XAUTOCLAIM wrappers, group/consumer naming, the worker
heartbeat key, and the authoritative click-event payload (de)serializer shared by
the redirect producer and worker consumer. Implemented in Epic 5.
"""
