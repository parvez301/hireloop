from hireloop.core.scanner.adapters.base import ListingPayload
from hireloop.core.scanner.dedup import compute_content_hash


def _listing(**overrides) -> ListingPayload:
    defaults = dict(
        title="Senior Engineer",
        company="acme",
        location="Remote",
        salary_min=None,
        salary_max=None,
        employment_type="full_time",
        seniority="senior",
        description_md="Build things.",
        requirements_json={"skills": ["python"]},
        source_url="https://example.com/1",
    )
    defaults.update(overrides)
    return ListingPayload(**defaults)


def test_same_description_same_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="Build things.")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_whitespace_differences_same_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="  Build things.  \n")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_different_description_different_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="Destroy things.")
    assert compute_content_hash(a) != compute_content_hash(b)


def test_different_requirements_different_hash() -> None:
    a = _listing(requirements_json={"skills": ["python"]})
    b = _listing(requirements_json={"skills": ["ruby"]})
    assert compute_content_hash(a) != compute_content_hash(b)


def test_source_url_not_part_of_hash() -> None:
    """Two boards hosting the same JD dedupe to one hash."""
    a = _listing(source_url="https://a.com/1")
    b = _listing(source_url="https://b.com/2")
    assert compute_content_hash(a) == compute_content_hash(b)
