"""Tests for the cast, which since 2026-10-17 is real people (Q2.1, Q2.4).

Most of these guard data rather than code. That is the point: the facts in
cast.json are claims about named individuals, and the cheapest place to catch a
missing source or an un-briefed likeness is before anything is drawn.
"""

from __future__ import annotations

import pytest

from owp.acquisition.curated import CuratedTargetSource
from owp.cast import Cast, Character


def test_the_cast_loads() -> None:
    assert Cast.load().characters


def test_character_ids_are_unique() -> None:
    characters = Cast.load().characters
    assert len({c.id for c in characters}) == len(characters)


def test_the_cast_is_the_ceos_of_the_covered_companies() -> None:
    cast = Cast.load()
    assert cast.real_people() == cast.characters
    assert all(c.company and c.title for c in cast.characters)


def test_every_curated_target_has_someone_to_deliver_it() -> None:
    slugs = [t.slug for t in CuratedTargetSource().targets()]
    assert Cast.load().missing_for(slugs) == []


def test_the_right_ceo_speaks_for_a_target() -> None:
    character = Cast.load().for_target("instagram")
    assert character.id == "zuckerberg"
    assert character.company == "Meta Platforms"


def test_a_target_nobody_covers_says_what_to_add() -> None:
    with pytest.raises(KeyError, match="publishes its policy"):
        Cast.load().for_target("whatsapp")


def test_missing_targets_are_reported_not_raised() -> None:
    # Like CuratedTargetSource.shortfall: the list is still a placeholder, so
    # an incomplete cast has to be visible without breaking every command.
    assert Cast.load().missing_for(["instagram", "whatsapp"]) == ["whatsapp"]


def test_one_ceo_can_cover_several_targets() -> None:
    # Meta publishes one policy for Instagram, Facebook, WhatsApp and Threads,
    # so the cast stays smaller than the target list and the same drawn person
    # recurs across all of a company's videos (Q2.4).
    cast = Cast(
        characters=[
            Character(
                id="zuckerberg",
                name="Mark Zuckerberg",
                role="r",
                appearance="caricature",
                real_person=True,
                target_slugs=["instagram", "facebook", "whatsapp"],
            )
        ]
    )
    assert cast.for_target("whatsapp").id == cast.for_target("instagram").id


def test_every_real_person_records_who_checked_and_when() -> None:
    # A video in which last quarter's CEO explains this quarter's policy is
    # wrong about a named person, and review will not catch it: the face looks
    # right. Provenance is the only thing that makes it checkable.
    for character in Cast.load().real_people():
        assert character.verified_on is not None, character.id
        assert character.source, character.id


def test_every_real_persons_appearance_is_briefed_as_a_caricature() -> None:
    # The one automatable part of "never a likeness that could pass as
    # footage": the brief an artist or an image model is handed has to say so.
    for character in Cast.load().real_people():
        assert "caricature" in character.appearance.lower(), character.id


def test_real_people_get_plainly_synthetic_voices() -> None:
    # A cloned voice would make the video an impersonation rather than
    # commentary, so every voice is an off-the-shelf TTS id (Q2.5).
    for character in Cast.load().real_people():
        assert character.voice_id and character.voice_id.startswith("en-US-")
