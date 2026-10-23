from dataclasses import dataclass, field
from enum import Enum

from keboola.component.exceptions import UserException


# configuration keys that differ from the snake_case field names
CONFIG_KEYS = {"auth_type": "authType"}


# the encrypted keys (prefixed with # in Keboola) have to be prefixed with "encrypted_" here
def config_keys(key: str) -> str:
    key = CONFIG_KEYS.get(key, key)
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


AUTH_TYPE_ORGANIZATION = "organization"


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
    auth_type: str | None = None
    encrypted_token: str | None = None
    ssh_keys: SSHKeysConfiguration = field(default_factory=SSHKeysConfiguration)

    def validate_auth(self) -> None:
        if self.auth_type not in (None, "", AUTH_TYPE_ORGANIZATION):
            raise UserException(
                f'Invalid git authType "{self.auth_type}": only "{AUTH_TYPE_ORGANIZATION}" is supported'
            )
        if self.uses_organization_auth and self.auth != AuthEnum.NONE:
            raise UserException(
                f'Use either "authType: {AUTH_TYPE_ORGANIZATION}" or explicit credentials ("pat", "ssh"), not both'
            )

    @property
    def uses_organization_auth(self) -> bool:
        return self.auth_type == AUTH_TYPE_ORGANIZATION


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
