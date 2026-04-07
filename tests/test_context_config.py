"""Tests for context_config.py — loading personal context from TOML."""

from context_config import load_context, PersonalContext, ChildContext


class TestLoadContext:
    def test_missing_file_returns_empty(self, tmp_path):
        result = load_context(tmp_path / "nonexistent.toml")
        assert result == PersonalContext()
        assert result.children == ()

    def test_malformed_file_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.toml"
        bad.write_text("this is not valid toml {{{{")
        result = load_context(bad)
        assert result.children == ()

    def test_no_child_section_returns_empty(self, tmp_path):
        f = tmp_path / "context.toml"
        f.write_text('[other]\nkey = "value"\n')
        result = load_context(f)
        assert result.children == ()

    def test_singular_child_backcompat(self, tmp_path):
        """[child] singular table still works."""
        f = tmp_path / "context.toml"
        f.write_text(
            '[child]\n'
            'name = "Alex"\n'
            'grade = 7\n'
            'school = "Lincoln Middle School"\n'
            'sports = ["soccer", "swim team"]\n'
            'activities = ["robotics club"]\n'
            'teachers = ["Ms. Johnson (Math)", "Mr. Lee (Science)"]\n'
        )
        result = load_context(f)
        assert len(result.children) == 1
        child = result.children[0]
        assert child.name == "Alex"
        assert child.grade == 7
        assert child.school == "Lincoln Middle School"
        assert child.sports == ("soccer", "swim team")
        assert child.activities == ("robotics club",)
        assert child.teachers == ("Ms. Johnson (Math)", "Mr. Lee (Science)")

    def test_multiple_children(self, tmp_path):
        f = tmp_path / "context.toml"
        f.write_text(
            '[[children]]\n'
            'name = "Giselle"\n'
            'grade = 5\n'
            'school = "Synapse School"\n'
            'teachers = ["Ms. Chaney (Language Arts)"]\n'
            '\n'
            '[[children]]\n'
            'name = "Sophie"\n'
            'grade = 3\n'
            'school = "Synapse School"\n'
            'teachers = ["Mr. Smith (Math)"]\n'
        )
        result = load_context(f)
        assert len(result.children) == 2
        assert result.children[0].name == "Giselle"
        assert result.children[0].teachers == ("Ms. Chaney (Language Arts)",)
        assert result.children[1].name == "Sophie"
        assert result.children[1].teachers == ("Mr. Smith (Math)",)

    def test_minimal_child(self, tmp_path):
        f = tmp_path / "context.toml"
        f.write_text('[child]\nname = "Sam"\n')
        result = load_context(f)
        assert len(result.children) == 1
        assert result.children[0].name == "Sam"
        assert result.children[0].teachers == ()
        assert result.children[0].sports == ()

    def test_frozen_dataclass(self, tmp_path):
        f = tmp_path / "context.toml"
        f.write_text('[child]\nname = "Alex"\n')
        result = load_context(f)
        import pytest
        with pytest.raises(AttributeError):
            result.children = ()
