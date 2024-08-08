import logging
import colorlog

def configure_logger(name, color):
  logger = colorlog.getLogger(name)
  logger.setLevel(logging.INFO)
  
  handler = logging.StreamHandler()
  formatter = colorlog.ColoredFormatter(
    '%(asctime)s - %(log_color)s%(levelname)s%(reset)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
      'DEBUG': color,
      'INFO': color,
      'WARNING': 'yellow',
      'ERROR': 'red',
      'CRITICAL': 'bold_red',
    }
  )
  handler.setFormatter(formatter)
  logger.addHandler(handler)
  return logger