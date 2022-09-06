import logging
from typing import Dict

from asyncpraw.models import Subreddit
from asyncpraw.models.reddit.removal_reasons import RemovalReason

from .ruleset_schemas import PostFlairSettings, RemovalReasonSettings, Ruleset

log: logging.Logger = logging.getLogger(__name__)


async def get_current_post_flair(subreddit: Subreddit) -> Dict[str, PostFlairSettings]:
    """Get the post flair currently defined in a subreddit

    Args:
        subreddit (Subreddit)

    Returns:
        Dict[str, PostFlairSettings]: Dict with keys being flair titles and values being PostFlairSettings
    """
    return {
        flair["text"]: PostFlairSettings.parse_obj(flair)
        async for flair in subreddit.flair.link_templates
    }


async def get_current_removal_reasons(
    subreddit: Subreddit,
) -> Dict[str, RemovalReasonSettings]:
    """Get the removal reasons currently defined in a subreddit

    Args:
        subreddit (Subreddit)

    Returns:
        Dict[str, RemovalReasonSettings]: Dict with keys being removal reason titles and values being RemovalReasonSettings
    """
    return {
        reason.title: RemovalReasonSettings.parse_obj(reason.__dict__)
        async for reason in subreddit.mod.removal_reasons
    }


async def sync_removal_reasons(
    subreddit: Subreddit, rr_rules: Dict[str, RemovalReasonSettings]
) -> None:
    """Synchronize sub removal reasons with what's defined in the "removal_reasons" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
        subreddit (Subreddit): The subreddit in which to act
        rr_rules (Dict[str, RemovalReasonSettings]): The removal reasons section of the rules file
    """
    existing_reasons: Dict[
        str, RemovalReasonSettings
    ] = await get_current_removal_reasons(subreddit)

    for reason in rr_rules:
        if reason in existing_reasons:
            if rr_rules[reason] != existing_reasons[reason]:
                log.info("Updating removal reason: %s", reason)
                r: RemovalReason = await subreddit.mod.removal_reasons.get_reason(
                    existing_reasons[reason].id
                )
                await r.update(message=rr_rules[reason].message)
            else:
                log.debug(
                    'Removal reason rule "%s" matches existing removal reason.  Skipping.',
                    reason,
                )
        else:
            log.info("Adding removal reason: %s", reason)
            await subreddit.mod.removal_reasons.add(
                message=rr_rules[reason].message, title=reason
            )

    return


async def sync_post_flair(
    subreddit: Subreddit, pf_rules: Dict[str, PostFlairSettings]
) -> None:
    """Synchronize sub post flair with what's defined in the "post_flair" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
        subreddit (Subreddit): The subreddit in which to act
        pf_rules (Dict[str, PostFlairSettings]): The post flair section of the rules file
    """

    existing_flairs: Dict[str, PostFlairSettings] = await get_current_post_flair(
        subreddit
    )

    for flair in pf_rules:
        if flair in existing_flairs:
            if pf_rules[flair] != existing_flairs[flair]:
                log.info("Updaing post flair: %s", flair)
                await subreddit.flair.link_templates.update(
                    template_id=existing_flairs[flair].id,
                    text=flair,
                    css_class=pf_rules[flair].css_class,
                    background_color=pf_rules[flair].background_color,
                    text_color=pf_rules[flair].text_color,
                    mod_only=pf_rules[flair].mod_only,
                    fetch=True,
                )
            else:
                log.debug(
                    'Post flair rule "%s" matches existing post flair.  Skipping.',
                    flair,
                )
        else:
            log.info("Adding post flair: %s", flair)
            await subreddit.flair.link_templates.add(
                text=flair,
                css_class=pf_rules[flair].css_class,
                background_color=pf_rules[flair].background_color,
                text_color=pf_rules[flair].text_color,
                mod_only=pf_rules[flair].mod_only,
            )


async def dump_current_settings(subreddit: Subreddit, output_file: str) -> None:
    """Dump a subreddit's current post flair and removal reasons to a file in yaml format.

    Args:
        subreddit (Subreddit): The subreddit to read from
        output_file (str): The file to write to
    """
    ruleset = Ruleset(flair_actions=None, post_flair=None, removal_reasons=None)

    ruleset.post_flair = await get_current_post_flair(subreddit)

    ruleset.removal_reasons = await get_current_removal_reasons(subreddit)

    with open(output_file, "wt", encoding="utf-8") as f:
        f.write(ruleset.yaml())
