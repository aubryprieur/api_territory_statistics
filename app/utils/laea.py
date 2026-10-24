"""
Projection inverse ETRS89-LAEA (EPSG:3035) → WGS84 (longitude, latitude), formule de l'IOGP (guidance note 7-2,
méthode 9820), sans dépendance externe. Sert à calculer les coins des carreaux Insee (identifiants
CRS3035RES1000mN{y}E{x} : coin inférieur gauche en LAEA). Écart avec pyproj < 1e-12 degré.
"""
import math
A = 6378137.0
F = 1 / 298.257222101
E2 = 2 * F - F * F
E = math.sqrt(E2)
LAT0, LON0 = math.radians(52.0), math.radians(10.0)
FE, FN = 4321000.0, 3210000.0

def _q(phi):
    s = math.sin(phi)
    return (1 - E2) * (s / (1 - E2 * s * s) - (1 / (2 * E)) * math.log((1 - E * s) / (1 + E * s)))

QP = _q(math.pi / 2)
Q0 = _q(LAT0)
B0 = math.asin(Q0 / QP)
RQ = A * math.sqrt(QP / 2)
D = A * math.cos(LAT0) / (math.sqrt(1 - E2 * math.sin(LAT0) ** 2) * RQ * math.cos(B0))

def laea_to_wgs84(x, y):
    dx, dy = x - FE, y - FN
    rho = math.sqrt((dx / D) ** 2 + (D * dy) ** 2)
    if rho == 0:
        return math.degrees(LON0), math.degrees(LAT0)
    c = 2 * math.asin(rho / (2 * RQ))
    beta = math.asin(math.cos(c) * math.sin(B0) + D * dy * math.sin(c) * math.cos(B0) / rho)
    lam = LON0 + math.atan2(dx * math.sin(c), D * rho * math.cos(B0) * math.cos(c) - D * D * dy * math.sin(B0) * math.sin(c))
    e4, e6 = E2 * E2, E2 * E2 * E2
    phi = (beta + (E2 / 3 + 31 * e4 / 180 + 517 * e6 / 5040) * math.sin(2 * beta)
           + (23 * e4 / 360 + 251 * e6 / 3780) * math.sin(4 * beta) + (761 * e6 / 45360) * math.sin(6 * beta))
    return math.degrees(lam), math.degrees(phi)
