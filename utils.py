import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)

def log(msg):
    logging.info(msg)

def safe_text(node):
    try:
        return node.inner_text().strip()
    except:
        return ""
