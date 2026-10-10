"""Application volontairement vulnérable — cible du Test Lab SecuMerge.

⚠️  NE PAS UTILISER EN PRODUCTION. Ce fichier existe uniquement pour que
les scanners du labo (Semgrep) détectent des problèmes de sécurité.
Les vulnérabilités sont intentionnelles et isolées du vrai backend.
"""

import subprocess

import yaml

# Secret en dur (volontaire) : CWE-798.
API_TOKEN = "lab-secret-token-123"
DB_PASSWORD = "SuperSecret123!"


def calculate(expression: str):
    """Exécute une expression fournie par l'utilisateur (eval)."""
    return eval(expression)


def run_command(user_input: str) -> None:
    """Construit une commande shell avec une entrée non fiable."""
    subprocess.run("ls " + user_input, shell=True)


def load_config(raw: str):
    """Charge du YAML avec le loader par défaut (dangereux)."""
    return yaml.load(raw)
