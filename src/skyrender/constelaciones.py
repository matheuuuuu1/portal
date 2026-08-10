"""Líneas de constelaciones dibujadas a partir del catálogo (Fase 7).

Cada segmento es un par de designaciones Bayer + genitivo tal como se
buscan en el catálogo (p. ej. "Alp Ori", "Gam Leo"). El número de
componente del BSC (p. ej. "41Gam1Leo" = Gamma-1 Leonis) se resuelve con
`Catalogo.buscar_designacion`, que normaliza espacios y dígitos.

Son las constelaciones más representativas para latitud ~10°N (muchas
cubren tanto el hemisferio norte como el sur, ver Orión, Escorpio, la
Cruz del Sur y Carina según la estación).
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalogo import Catalogo, Estrella

_ES = (
    # Osa Mayor (el carro)
    "Alp UMa", "Bet UMa", "Gam UMa", "Del UMa", "Eps UMa", "Zet UMa", "Eta UMa",
    # Osa Menor
    "Alp UMi", "Bet UMi", "Gam UMi",
    # Orión
    "Alp Ori", "Bet Ori", "Gam Ori", "Del Ori", "Eps Ori", "Zet Ori", "Kap Ori",
    # Tauro
    "Alp Tau", "Bet Tau", "Eta Tau", "Gam Tau",
    # Géminis
    "Alp Gem", "Bet Gem", "Gam Gem",
    # Leo
    "Alp Leo", "Bet Leo", "Gam Leo",
    # Casiopea
    "Alp Cas", "Bet Cas", "Gam Cas", "Del Cas", "Eps Cas",
    # Lira
    "Alp Lyr", "Bet Lyr", "Gam Lyr",
    # Águila
    "Alp Aql", "Bet Aql", "Gam Aql",
    # Cisne
    "Alp Cyg", "Bet Cyg", "Gam Cyg", "Del Cyg", "Eps Cyg",
    # Escorpio
    "Alp Sco", "Bet Sco", "Del Sco", "Pi Sco", "Lam Sco", "The Sco", "Sig Sco",
    # Sagitario
    "Eps Sgr", "Del Sgr", "Lam Sgr", "Sig Sgr",
    # Andrómeda
    "Alp And", "Bet And", "Gam And",
    # Pegaso
    "Alp Peg", "Bet Peg", "Gam Peg", "Eps Peg",
    # Cruz del Sur
    "Alp Cru", "Bet Cru", "Gam Cru", "Del Cru", "Eps Cru",
    # Can Mayor
    "Alp CMa", "Bet CMa", "Del CMa", "Eps CMa", "Eta CMa",
    # Carina
    "Alp Car", "Bet Car", "Eps Car",
    # --- Constelaciones adicionales (lat 10°N) ---
    # Ofiuco
    "Alp Oph", "Eps Oph", "Zet Oph", "Lam Oph", "Del Oph", "Bet Oph",
    # Hidra (tramo central)
    "Alp Hya", "Bet Hya", "Gam Hya", "Del Hya", "Eps Hya",
    "Zet Hya", "Eta Hya", "Iot Hya", "Lam Hya",
    # Centauro
    "Alp1Cen", "Bet1Cen", "Gam Cen", "Del Cen", "Eps Cen",
    "Zet Cen", "Eta Cen", "Iot Cen", "Kap Cen", "Lam Cen",
    # Lobo
    "Bet Lup", "Gam Lup", "Del Lup", "Eps Lup",
    "Zet Lup", "Eta Lup", "Iot Lup", "Kap1Lup", "Lam Lup",
    # Ara
    "Bet Ara", "Gam Ara", "Del Ara", "Eps Ara", "Zet Ara", "Eta Ara", "Iot Ara",
    # Corona Boreal
    "Alp CrB", "Bet CrB", "Gam CrB", "Del CrB", "Eps CrB", "Zet CrB",
    # Hércules
    "Alp Her", "Bet Her", "Gam Her", "Del Her",
    "Eps Her", "Zet Her", "Eta Her",
    # Draco (cabeza del dragón)
    "Alp Dra", "Bet Dra", "Gam Dra", "Del Dra",
    "Eps Dra", "Zet Dra", "Eta Dra", "Iot Dra", "Kap Dra",
)


@dataclass(frozen=True)
class Constelacion:
    nombre: str
    segmentos: tuple[tuple[str, str], ...]


CONSTELACIONES: tuple[Constelacion, ...] = (
    Constelacion("Osa Mayor", (
        ("Alp UMa", "Bet UMa"), ("Bet UMa", "Gam UMa"),
        ("Gam UMa", "Del UMa"), ("Del UMa", "Alp UMa"),
        ("Del UMa", "Eps UMa"), ("Eps UMa", "Zet UMa"),
        ("Zet UMa", "Eta UMa"),
    )),
    Constelacion("Osa Menor", (
        ("Alp UMi", "Bet UMi"), ("Bet UMi", "Gam UMi"),
    )),
    Constelacion("Orión", (
        ("Alp Ori", "Gam Ori"), ("Alp Ori", "Zet Ori"),
        ("Zet Ori", "Eps Ori"), ("Eps Ori", "Del Ori"),
        ("Del Ori", "Bet Ori"), ("Del Ori", "Kap Ori"),
        ("Bet Ori", "Kap Ori"), ("Gam Ori", "Del Ori"),
    )),
    Constelacion("Tauro", (
        ("Alp Tau", "Eta Tau"), ("Alp Tau", "Gam Tau"),
        ("Alp Tau", "Bet Tau"), ("Gam Tau", "Alp Tau"),
    )),
    Constelacion("Géminis", (
        ("Alp Gem", "Bet Gem"), ("Alp Gem", "Gam Gem"),
        ("Bet Gem", "Gam Gem"),
    )),
    Constelacion("Leo", (
        ("Alp Leo", "Gam Leo"), ("Gam Leo", "Bet Leo"),
    )),
    Constelacion("Casiopea", (
        ("Alp Cas", "Bet Cas"), ("Bet Cas", "Gam Cas"),
        ("Gam Cas", "Del Cas"), ("Del Cas", "Eps Cas"),
    )),
    Constelacion("Lira", (
        ("Alp Lyr", "Bet Lyr"), ("Bet Lyr", "Gam Lyr"),
    )),
    Constelacion("Águila", (
        ("Gam Aql", "Bet Aql"), ("Bet Aql", "Alp Aql"),
    )),
    Constelacion("Cisne", (
        ("Alp Cyg", "Gam Cyg"), ("Gam Cyg", "Eps Cyg"),
        ("Gam Cyg", "Del Cyg"), ("Del Cyg", "Alp Cyg"),
        ("Alp Cyg", "Bet Cyg"), ("Bet Cyg", "Eps Cyg"),
    )),
    Constelacion("Escorpio", (
        ("Bet Sco", "Del Sco"), ("Del Sco", "Pi Sco"),
        ("Pi Sco", "Alp Sco"), ("Alp Sco", "Lam Sco"),
        ("Lam Sco", "The Sco"), ("The Sco", "Sig Sco"),
    )),
    Constelacion("Sagitario", (
        ("Eps Sgr", "Del Sgr"), ("Del Sgr", "Lam Sgr"),
        ("Lam Sgr", "Sig Sgr"), ("Sig Sgr", "Eps Sgr"),
    )),
    Constelacion("Andrómeda", (
        ("Alp And", "Bet And"), ("Bet And", "Gam And"),
    )),
    Constelacion("Pegaso", (
        ("Alp Peg", "Bet Peg"), ("Bet Peg", "Gam Peg"),
        ("Gam Peg", "Alp Peg"), ("Bet Peg", "Eps Peg"),
    )),
    Constelacion("Cruz del Sur", (
        ("Alp Cru", "Gam Cru"), ("Gam Cru", "Del Cru"),
        ("Del Cru", "Eps Cru"), ("Eps Cru", "Alp Cru"),
        ("Alp Cru", "Bet Cru"),
    )),
    Constelacion("Can Mayor", (
        ("Bet CMa", "Alp CMa"), ("Alp CMa", "Eta CMa"),
        ("Eta CMa", "Del CMa"), ("Del CMa", "Eps CMa"),
    )),
    Constelacion("Carina", (
        ("Alp Car", "Bet Car"), ("Bet Car", "Eps Car"),
    )),
    Constelacion("Ofiuco", (
        ("Alp Oph", "Eps Oph"), ("Eps Oph", "Zet Oph"),
        ("Zet Oph", "Lam Oph"), ("Lam Oph", "Del Oph"),
        ("Del Oph", "Bet Oph"),
    )),
    Constelacion("Hidra", (
        ("Alp Hya", "Bet Hya"), ("Bet Hya", "Gam Hya"),
        ("Gam Hya", "Del Hya"), ("Del Hya", "Eps Hya"),
        ("Eps Hya", "Zet Hya"), ("Zet Hya", "Eta Hya"),
        ("Eta Hya", "Iot Hya"), ("Iot Hya", "Lam Hya"),
    )),
    Constelacion("Centauro", (
        ("Alp1Cen", "Bet1Cen"), ("Bet1Cen", "Gam Cen"),
        ("Gam Cen", "Del Cen"), ("Del Cen", "Eps Cen"),
        ("Eps Cen", "Zet Cen"), ("Zet Cen", "Eta Cen"),
        ("Eta Cen", "Iot Cen"), ("Iot Cen", "Kap Cen"),
        ("Kap Cen", "Lam Cen"),
    )),
    Constelacion("Lobo", (
        ("Bet Lup", "Gam Lup"), ("Gam Lup", "Del Lup"),
        ("Del Lup", "Eps Lup"), ("Eps Lup", "Zet Lup"),
        ("Zet Lup", "Eta Lup"), ("Eta Lup", "Iot Lup"),
        ("Iot Lup", "Kap1Lup"), ("Kap1Lup", "Lam Lup"),
    )),
    Constelacion("Ara", (
        ("Bet Ara", "Gam Ara"), ("Gam Ara", "Del Ara"),
        ("Del Ara", "Eps Ara"), ("Eps Ara", "Zet Ara"),
        ("Zet Ara", "Eta Ara"), ("Eta Ara", "Iot Ara"),
    )),
    Constelacion("Corona Boreal", (
        ("Alp CrB", "Bet CrB"), ("Bet CrB", "Gam CrB"),
        ("Gam CrB", "Del CrB"), ("Del CrB", "Eps CrB"),
        ("Eps CrB", "Alp CrB"), ("Eps CrB", "Zet CrB"),
    )),
    Constelacion("Hércules", (
        ("Alp Her", "Bet Her"), ("Bet Her", "Eps Her"),
        ("Eps Her", "Eta Her"), ("Eta Her", "Zet Her"),
        ("Zet Her", "Del Her"), ("Del Her", "Gam Her"),
    )),
    Constelacion("Draco", (
        ("Alp Dra", "Bet Dra"), ("Bet Dra", "Gam Dra"),
        ("Gam Dra", "Del Dra"), ("Del Dra", "Eps Dra"),
        ("Eps Dra", "Zet Dra"), ("Zet Dra", "Eta Dra"),
        ("Eta Dra", "Iot Dra"), ("Iot Dra", "Kap Dra"),
    )),
)


def segmentos(catalogo: Catalogo) -> list[tuple[Estrella, Estrella]]:
    """Resuelve los segmentos a pares de estrellas reales del catálogo.

    Se omiten los segmentos cuyos extremos no estén en el catálogo (p. ej.
    una estrella de componente 2 que el BSC no liste).
    """
    resueltos: list[tuple[Estrella, Estrella]] = []
    vistos: set[int] = set()
    for constelacion in CONSTELACIONES:
        for a, b in constelacion.segmentos:
            ea = catalogo.buscar_designacion(a)
            eb = catalogo.buscar_designacion(b)
            if ea is None or eb is None or ea.id == eb.id:
                continue
            # Evita duplicar un segmento ya añadido por otra constelación.
            par = (min(ea.id, eb.id), max(ea.id, eb.id))
            if par in vistos:
                continue
            vistos.add(par)
            resueltos.append((ea, eb))
    return resueltos
