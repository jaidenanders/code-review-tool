"""TDD tests for profile_service — review focus profiles."""
import pytest
from app.services.profile_service import get_profile, list_profiles, ReviewProfile, PROFILES


class TestProfileDefinitions:
    def test_four_profiles_exist(self):
        assert len(PROFILES) == 4

    def test_all_required_profiles_present(self):
        ids = {p.id for p in PROFILES.values()}
        assert ids == {"general", "security", "performance", "style"}

    def test_every_profile_has_non_empty_name(self):
        for p in PROFILES.values():
            assert p.name.strip(), f"{p.id} has empty name"

    def test_every_profile_has_non_empty_description(self):
        for p in PROFILES.values():
            assert p.description.strip(), f"{p.id} has empty description"

    def test_general_profile_has_no_focus_instructions(self):
        assert PROFILES["general"].focus_instructions == ""

    def test_security_profile_mentions_injection(self):
        assert "injection" in PROFILES["security"].focus_instructions.lower()

    def test_security_profile_mentions_authentication(self):
        assert "auth" in PROFILES["security"].focus_instructions.lower()

    def test_performance_profile_mentions_complexity(self):
        assert "complex" in PROFILES["performance"].focus_instructions.lower()

    def test_style_profile_mentions_naming(self):
        assert "nam" in PROFILES["style"].focus_instructions.lower()


class TestGetProfile:
    def test_returns_correct_profile_by_id(self):
        p = get_profile("security")
        assert p.id == "security"

    def test_returns_general_for_unknown_id(self):
        p = get_profile("nonexistent")
        assert p.id == "general"

    def test_returns_general_when_none_passed(self):
        p = get_profile(None)
        assert p.id == "general"

    def test_returns_ReviewProfile_instance(self):
        assert isinstance(get_profile("performance"), ReviewProfile)

    def test_all_valid_ids_resolve(self):
        for profile_id in ["general", "security", "performance", "style"]:
            p = get_profile(profile_id)
            assert p.id == profile_id


class TestListProfiles:
    def test_returns_list(self):
        assert isinstance(list_profiles(), list)

    def test_returns_all_four(self):
        assert len(list_profiles()) == 4

    def test_general_is_first(self):
        assert list_profiles()[0].id == "general"

    def test_each_item_is_ReviewProfile(self):
        for p in list_profiles():
            assert isinstance(p, ReviewProfile)
