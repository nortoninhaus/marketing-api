from pathlib import Path


def test_mcp_dependency_excludes_breaking_v2():
    requirements = Path(__file__).resolve().parents[1].joinpath("requirements.txt").read_text().splitlines()

    assert "mcp>=1.6.0,<2" in requirements
