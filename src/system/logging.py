import json
import logging
from datetime import datetime, timezone
from src.system.paths import ROOT

class JsonFormatter(logging.Formatter):
    def format(self, record):
        item = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': record.levelname, 'message': record.getMessage()}
        if record.exc_info:
            item['traceback'] = self.formatException(record.exc_info)
        return json.dumps(item, ensure_ascii=False)

def get_logger():
    logger = logging.getLogger('fakeobject')
    if not logger.handlers:
        handler = logging.FileHandler(ROOT / 'logs/app.log', encoding='utf-8')
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
