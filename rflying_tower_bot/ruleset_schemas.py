import logging
from typing import Annotated, Dict, List, Optional, Self, Union

from pydantic import BaseModel, Field, model_validator

log: logging.Logger = logging.getLogger(__name__)


class FlairAction(BaseModel):
    action: str
    argument: Union[str, int, None] = None

    @model_validator(mode="after")
    def valid_action(self) -> Self:
        valid_actions = ["comment", "remove", "remove_with_reason"]
        if self.action not in valid_actions:
            raise ValueError(f"{self.action} is not a valid action")

        actions_requiring_arguments = ["comment", "remove_with_reason"]
        if self.action in actions_requiring_arguments and (self.argument is None):
            raise ValueError(f"Action {self.action} requires an argument")

        return self


class PostFlairSettings(BaseModel):
    css_class: str = ""
    background_color: str = "#dadada"
    text_color: str = "dark"
    mod_only: bool = True
    id: Annotated[Optional[str], Field(exclude=True)] = None


class RemovalReasonSettings(BaseModel):
    message: str
    id: Annotated[Optional[str], Field(exclude=True)] = None


class Ruleset(BaseModel):
    flair_actions: Optional[Dict[str, List[FlairAction]]] = None
    post_flair: Optional[Dict[str, PostFlairSettings]] = None
    removal_reasons: Optional[Dict[str, RemovalReasonSettings]] = None
