"""Module provides the schema definitions for the ruleset."""

import logging
from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

log: logging.Logger = logging.getLogger(__name__)


class FlairAction(BaseModel):
    """Represents a flair action."""

    action: str
    argument: str | int | None = None

    @model_validator(mode="after")
    def valid_action(self) -> Self:
        """Validate the action and argument of the FlairAction."""
        valid_actions = ["comment", "remove", "remove_with_reason"]
        if self.action not in valid_actions:
            raise ValueError(f"{self.action} is not a valid action")

        actions_requiring_arguments = ["comment", "remove_with_reason"]
        if self.action in actions_requiring_arguments and (self.argument is None):
            raise ValueError(f"Action {self.action} requires an argument")

        return self


class PostFlairSettings(BaseModel):
    """
    Represents the settings for post flair.

    Attributes
    ----------
        css_class (str): The CSS class for the post flair.
        background_color (str): The background color for the post flair.
        text_color (str): The text color for the post flair.
        mod_only (bool): Indicates if the post flair is only visible to moderators.
        id (str | None): The ID of the post flair.

    """

    css_class: str = ""
    background_color: str = "#dadada"
    text_color: str = "dark"
    mod_only: bool = True
    id: Annotated[str | None, Field(exclude=True)] = None


class RemovalReasonSettings(BaseModel):
    """Represents the settings for removal reasons."""

    message: str
    id: Annotated[str | None, Field(exclude=True)] = None


class Ruleset(BaseModel):
    """Represents the ruleset."""

    flair_actions: dict[str, list[FlairAction]] | None = None
    post_flair: dict[str, PostFlairSettings] | None = None
    removal_reasons: dict[str, RemovalReasonSettings] | None = None
