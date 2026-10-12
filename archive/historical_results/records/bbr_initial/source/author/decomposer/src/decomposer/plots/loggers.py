import logging

# Configure root logger (optional)
logging.basicConfig(level=logging.INFO)

LOGGER_FLOW = logging.getLogger("INFO")
LOGGER_FLOW.setLevel(logging.INFO)

# Define rank.base logger
LOGGER_BASE = logging.getLogger("RANK.BASE")
LOGGER_BASE.setLevel(logging.INFO)

# Custom handler and formatter
handler = logging.StreamHandler()
formatter = logging.Formatter('[%(name)s] %(asctime)s: %(message)s')
handler.setFormatter(formatter)

# Define rank.decomp logger
LOGGER_DECOMP = logging.getLogger("RANK.DECOMP")
LOGGER_DECOMP.setLevel(logging.INFO)

# Attach the handler to both loggers
LOGGER_BASE.addHandler(handler)
LOGGER_DECOMP.addHandler(handler)
LOGGER_FLOW.addHandler(handler)


# LOGGER_BASE.setLevel(logging.CRITICAL + 1)
# LOGGER_DECOMP.setLevel(logging.CRITICAL + 1)