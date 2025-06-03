from dataclasses import dataclass, field
from enum import Enum


# the encrypted keys (prefixed with # in Keboola) have to be prefixed with "encrypted_" here
def encrypted_keys(key: str) -> str:
    return key.replace("encrypted_", "#") if key.startswith("encrypted_") else key


class SourceEnum(Enum):
    CODE = "code"
    GIT = "git"


@dataclass
class GitConfiguration:
    url: str = ""
    branch: str = "main"
    filename: str = "main.py"
    username: str | None = None  # not used at all, could be removed from the configuration
    encrypted_token: str | None = None
    encrypted_ssh_key: str | None = None


@dataclass
class Configuration:
    source: SourceEnum = SourceEnum.CODE
    packages: list[str] = field(default_factory=list)
    user_properties: dict[str, object] = field(default_factory=dict)
    code: str = ""
    git: GitConfiguration = field(default_factory=GitConfiguration)
