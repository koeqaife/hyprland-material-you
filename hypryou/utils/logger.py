import logging

logger = logging.getLogger("hypryou")


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m"
    }
    RESET = "\033[0m"
    BRIGHT = "\033[1m"

    def format(self, record: logging.LogRecord) -> str:
        log_color = self.COLORS.get(record.levelno, "\033[37m")
        levelname = record.levelname[0]
        formatted_message = super().format(record)
        return (
            f"{log_color}{levelname}{self.BRIGHT} " +
            formatted_message +
            self.RESET
        )


def setup_logger(level: int = logging.INFO) -> logging.Logger:
    handler = logging.StreamHandler()

    formatter = ColoredFormatter(
        '%(asctime)s [%(process)d]: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
