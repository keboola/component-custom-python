from dataclasses import dataclass, field
from enum import Enum


# the encrypted keys (prefixed with # in Keboola) have to be prefixed with "encrypted_" here
def encrypted_keys(key: str) -> str:
    return key.replace("encrypted_", "#") if key.startswith("encrypted_") else key


class SourceEnum(Enum):
    CODE = "code"
    GIT = "git"


class VenvEnum(Enum):
    BASE = "base"
    PY_3_12 = "3.12"
    PY_3_13 = "3.13"
    PY_3_14 = "3.14"


class AuthEnum(Enum):
    NONE = "none"
    PAT = "pat"
    SSH = "ssh"


# the ssh_keys.keys.[#private,public] structure is based on Keboola's standard SSH keys UI element output structure
@dataclass
class KeysConfiguration:
    public: str | None = None
    encrypted_private: str | None = None


@dataclass
class SSHKeysConfiguration:
    keys: KeysConfiguration = field(default_factory=KeysConfiguration)


@dataclass
class GitConfiguration:
    url: str = ""
    branch: str = "main"
    filename: str = "main.py"
    auth: AuthEnum = AuthEnum.NONE
    encrypted_token: str | None = None
    ssh_keys: SSHKeysConfiguration = field(default_factory=SSHKeysConfiguration)


@dataclass
class Configuration:
    source: SourceEnum = SourceEnum.CODE
    user_properties: dict[str, object] = field(default_factory=dict)
    venv: VenvEnum = VenvEnum.BASE
    packages: list[str] = field(default_factory=list)
    code: str = ""
    git: GitConfiguration = field(default_factory=GitConfiguration)
