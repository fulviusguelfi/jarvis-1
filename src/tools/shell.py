import subprocess
import sys


def run_shell(command: str, timeout: int = 10) -> str:
    """Executa comando shell e retorna stdout+stderr truncados."""
    try:
        if sys.platform.startswith("win"):
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        output = (result.stdout + result.stderr).strip()
        return output[:2000] if output else "(sem saída)"
    except subprocess.TimeoutExpired:
        return f"Timeout após {timeout}s"
    except Exception as e:
        return f"Erro: {e}"
