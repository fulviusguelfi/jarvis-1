from tools.shell import run_shell

TOOL_HANDLERS = {
    "run_shell": run_shell,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Executa um comando shell no computador do usuário e retorna a saída.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "O comando shell a executar (bash)."
                    }
                },
                "required": ["command"]
            }
        }
    }
]
