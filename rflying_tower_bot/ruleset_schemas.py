import logging
from typing import Any, Dict, List, Union

from pydantic import BaseModel, root_validator
from pydantic_yaml import YamlModel

log: logging.Logger = logging.getLogger(__name__)


class FlairAction(BaseModel):
    action: str
    argument: Union[str, int, None]

    @root_validator
    def valid_action(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        valid_actions = ["comment", "remove", "remove_with_reason"]
        if values["action"] not in valid_actions:
            raise ValueError(f"{values['action']} is not a valid action")

        actions_requiring_arguments = ["comment", "remove_with_reason"]
        if values["action"] in actions_requiring_arguments and (
            "argument" not in values or values["argument"] is None
        ):
            raise ValueError(f"Action {values['action']} requires an argument")

        return values


class PostFlairSettings(BaseModel):
    css_class: str = ""
    background_color: str = ""
    text_color: str = ""
    mod_only: bool = True


class Ruleset(YamlModel):
    flair_actions: Dict[str, List[FlairAction]]
    post_flair: Dict[str, PostFlairSettings]
