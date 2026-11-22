"""Service registry. Every service maps to services listed on Seva One (sevaone.karnataka.gov.in).
To add a service: create services/<name>.py with a Service subclass (set `dept` and `sevaone`)
and add it to _CLASSES below. Order in the menu follows Service.order."""
from .ahara import Ahara
from .bhoomi import Bhoomi
from .education import Education
from .energy import Energy
from .grievance import Grievance
from .gruhalakshmi import Gruhalakshmi
from .ksrtc import Ksrtc
from .revenue import Revenue
from .transport import Transport
from .yuvanidhi import Yuvanidhi

_CLASSES = [Revenue, Energy, Gruhalakshmi, Yuvanidhi, Education, Bhoomi, Ahara, Ksrtc, Transport, Grievance]

REGISTRY = {s.key: s for s in sorted((c() for c in _CLASSES), key=lambda s: s.order)}


def get(key):
    return REGISTRY.get(key)


def all_services():
    return list(REGISTRY.values())
