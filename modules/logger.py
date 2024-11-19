import logging

# Configurarea de bază a logger-ului
logging.basicConfig(
    filename="log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def log_info(message):
    """Loghează un mesaj de tip INFO."""
    logging.info(message)

def log_warning(message):
    """Loghează un mesaj de tip WARNING."""
    logging.warning(message)

def log_error(message):
    """Loghează un mesaj de tip ERROR."""
    logging.error(message)
