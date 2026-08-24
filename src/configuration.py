from dataclasses import dataclass, field
from enum import Enum

from keboola.component.exceptions import UserException


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
    OAUTH = "oauth"


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
    url_oauth: str = ""
    branch: str = "main"
    filename: str = "main.py"
    auth: AuthEnum = AuthEnum.NONE
    encrypted_token: str | None = None
    ssh_keys: SSHKeysConfiguration = field(default_factory=SSHKeysConfiguration)

    @property
    def repository_url(self) -> str:
        """Repository to clone. OAuth configurations select it from a list instead of typing in a URL."""
        return self.url_oauth if self.auth == AuthEnum.OAUTH else self.url


@dataclass
class Configuration:
    source: SourceEnum = SourceEnum.CODE
    user_properties: dict[str, object] | list = field(default_factory=dict)
    venv: VenvEnum = VenvEnum.BASE
    packages: list[str] = field(default_factory=list)
    code: str = ""
    git: GitConfiguration = field(default_factory=GitConfiguration)

    def __post_init__(self):
        if isinstance(self.user_properties, list):
            if len(self.user_properties) == 0:
                self.user_properties = {}
            else:
                raise UserException("Invalid user_properties: non-empty list not supported")
