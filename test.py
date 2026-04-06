import sys
sys.path.insert(0, '.')
from pydantic import ValidationError
from server.models import SREAction
try:
    a = SREAction.model_validate({'tool': 'list_alerts', 'params': {}})
    print(a)
except ValidationError as e:
    print(e)
