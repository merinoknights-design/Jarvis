"""
Módulo de Verificación Automática por Puntos de Sonda (PARTE B de la Adenda).
Utiliza trimesh y rtree para validar si puntos clave en zonas rayadas (material)
y zonas blancas (vacíos/huecos) se encuentran DENTRO o FUERA del sólido 3D.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np
import trimesh


def test_probe_points_on_stl(
    stl_path: Path,
    expected_probes: List[Dict[str, Any]]
) -> Dict[str, Any]:
    stl_path = Path(stl_path)
    if not stl_path.exists():
        return {
            "success": False,
            "error": f"Archivo STL no encontrado: {stl_path}",
            "passed_count": 0,
            "total_count": len(expected_probes),
            "results": []
        }

    mesh = trimesh.load(str(stl_path))
    
    # Detección automática de escala (Solid Edge exporta a veces en pulgadas si sestl.ini tiene Inch)
    # Si las cotas máximas son menores a 10 para piezas de cientos de mm, está en pulgadas
    max_bound = np.max(np.abs(mesh.bounds))
    if max_bound < 20.0:
        mesh.apply_scale(25.4)

    bounds = mesh.bounds.tolist()
    volume_mm3 = float(mesh.volume) if mesh.is_watertight else 0.0

    probe_points = [p["coords"] for p in expected_probes]
    contains_results = mesh.contains(probe_points)

    detailed_results = []
    passed_count = 0

    for i, p in enumerate(expected_probes):
        coords = p["coords"]
        expected_inside = p["debe_estar_dentro"]
        actual_inside = bool(contains_results[i])
        ok = (actual_inside == expected_inside)
        if ok:
            passed_count += 1
        detailed_results.append({
            "nombre": p["nombre"],
            "coords": coords,
            "zona": "RAYADA (Material)" if expected_inside else "BLANCA (Hueco/Vacio)",
            "esperado": "DENTRO" if expected_inside else "FUERA",
            "obtenido": "DENTRO" if actual_inside else "FUERA",
            "pasa": ok,
            "detalle": p.get("detalle", "")
        })

    all_passed = (passed_count == len(expected_probes))

    return {
        "success": all_passed,
        "is_watertight": bool(mesh.is_watertight),
        "bounds": bounds,
        "volume_mm3": volume_mm3,
        "passed_count": passed_count,
        "total_count": len(expected_probes),
        "results": detailed_results
    }


def get_standard_piston_probes() -> List[Dict[str, Any]]:
    return [
        {
            "nombre": "Corona maciza superior",
            "coords": [0.0, 0.0, -10.0],
            "debe_estar_dentro": True,
            "detalle": "z = -10 dentro de corona z in [0, -20]"
        },
        {
            "nombre": "Pared lateral alta",
            "coords": [140.0, 0.0, -40.0],
            "debe_estar_dentro": True,
            "detalle": "r = 140 en pared cilindrica [130, 150]"
        },
        {
            "nombre": "Pata sobre agujero",
            "coords": [70.0, 0.0, -120.0],
            "debe_estar_dentro": True,
            "detalle": "x = 70 en pata [50, 90], sobre z = -160"
        },
        {
            "nombre": "Pared central delantera",
            "coords": [0.0, 140.0, -170.0],
            "debe_estar_dentro": True,
            "detalle": "y = 140 en pared faldon delantero"
        },
        {
            "nombre": "Cavidad central",
            "coords": [0.0, 0.0, -100.0],
            "debe_estar_dentro": False,
            "detalle": "Hueco interior r < 130 bajo la corona"
        },
        {
            "nombre": "Agujero del pasador",
            "coords": [70.0, 0.0, -160.0],
            "debe_estar_dentro": False,
            "detalle": "Centro del taladro pasante R25"
        },
        {
            "nombre": "Zona cortada faldon R100",
            "coords": [140.0, 0.0, -150.0],
            "debe_estar_dentro": False,
            "detalle": "Vaciado lateral exterior bajo arco R100"
        },
        {
            "nombre": "Bajo borde faldon central",
            "coords": [0.0, 140.0, -190.0],
            "debe_estar_dentro": False,
            "detalle": "z = -190 debajo del faldon z = -180"
        }
    ]
