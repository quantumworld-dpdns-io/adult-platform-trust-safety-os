import os
import shlex
import subprocess
from typing import List, Optional


class CommandInjectionPrevention:
    DANGEROUS_CHARS = [";", "|", "&", "`", "$", "(", ")", "{", "}", "<", ">", "\n", "\r"]

    DANGEROUS_COMMANDS = [
        "rm", "dd", "mkfs", "format", "del", "rmdir",
        "shutdown", "reboot", "halt", "poweroff",
        "chmod", "chown", "chgrp", "passwd",
        "sudo", "su", "doas",
        "mount", "umount",
        "kill", "killall", "pkill",
        "curl", "wget", "nc", "netcat",
    ]

    def sanitize_command_args(self, args: List[str]) -> List[str]:
        sanitized = []
        for arg in args:
            arg = arg.replace("\x00", "")
            for char in self.DANGEROUS_CHARS:
                arg = arg.replace(char, "")
            sanitized.append(arg)
        return sanitized

    def validate_shell_input(self, input_str: str) -> tuple[bool, str]:
        if not input_str:
            return True, "Empty input"
        for char in self.DANGEROUS_CHARS:
            if char in input_str:
                return False, f"Dangerous character '{char}' detected"
        try:
            parts = shlex.split(input_str)
            for part in parts:
                for cmd in self.DANGEROUS_COMMANDS:
                    if part.lower() == cmd:
                        return False, f"Dangerous command '{cmd}' detected"
        except ValueError:
            return False, "Invalid shell syntax"
        return True, "Input is safe"

    def use_subprocess_safely(self, command: List[str], input_data: Optional[str] = None,
                               timeout: int = 30, cwd: Optional[str] = None) -> tuple[int, str, str]:
        sanitized = self.sanitize_command_args(command)
        try:
            result = subprocess.run(
                sanitized,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env=os.environ.copy(),
                shell=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -2, "", "Command not found"
        except PermissionError:
            return -3, "", "Permission denied"
        except Exception as e:
            return -4, "", str(e)

    def safe_exec(self, command: str, allowed_commands: Optional[List[str]] = None) -> tuple[bool, str]:
        is_valid, msg = self.validate_shell_input(command)
        if not is_valid:
            return False, msg
        try:
            parts = shlex.split(command)
        except ValueError:
            return False, "Invalid command syntax"
        if not parts:
            return False, "Empty command"
        if allowed_commands and parts[0] not in allowed_commands:
            return False, f"Command '{parts[0]}' not in allowed list"
        return True, command

    def wrap_command_with_limits(self, command: List[str], max_time: int = 10,
                                  max_output: int = 1024 * 1024) -> dict:
        sanitized = self.sanitize_command_args(command)
        return {
            "command": sanitized,
            "timeout": max_time,
            "capture_output": True,
            "text": True,
            "shell": False,
        }
