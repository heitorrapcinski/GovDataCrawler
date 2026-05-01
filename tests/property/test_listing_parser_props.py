"""Property-based tests for the ListingParser component.

Feature: gov-data-crawler
Property 1: parser extracts all embedded contract IDs

Validates: Requirements 1.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.listing import ListingParser


def _build_listing_html(contract_ids: list[str]) -> str:
    """Build a realistic listing page HTML with the given contract IDs.

    Each contract ID is embedded as a link following the ComprasNet pattern:
    <a href="/transparencia/contratos/{id}">Contract {id}</a>

    Args:
        contract_ids: List of numeric contract ID strings to embed.

    Returns:
        HTML string containing the contract links.
    """
    links = "\n".join(
        f'<a href="/transparencia/contratos/{cid}">Contract {cid}</a>'
        for cid in contract_ids
    )
    return f"""
    <html>
    <head><title>Contratos</title></head>
    <body>
        <div class="listing">
            {links}
        </div>
    </body>
    </html>
    """


# Strategy: generate a list of unique numeric contract ID strings
contract_id_strategy = st.text(
    alphabet=st.sampled_from("0123456789"),
    min_size=1,
    max_size=10,
)

unique_contract_ids_strategy = st.lists(
    contract_id_strategy,
    min_size=0,
    max_size=50,
    unique=True,
)


@settings(max_examples=100, deadline=1000)
@given(contract_ids=unique_contract_ids_strategy)
def test_parser_extracts_all_embedded_contract_ids(contract_ids: list[str]) -> None:
    """Property 1: For any valid listing page HTML containing a known set of
    contract ID links, the ListingParser.parse_contract_ids method SHALL return
    exactly the set of contract IDs embedded in the HTML, with no omissions
    and no duplicates.

    **Validates: Requirements 1.2**
    """
    html = _build_listing_html(contract_ids)
    parser = ListingParser()
    extracted_ids = parser.parse_contract_ids(html)

    # Exact match: same IDs, same count, no duplicates
    assert set(extracted_ids) == set(contract_ids)
    assert len(extracted_ids) == len(contract_ids)
    # No duplicates in output
    assert len(extracted_ids) == len(set(extracted_ids))
