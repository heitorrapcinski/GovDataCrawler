"""Property-based tests for contract detail URL construction.

Feature: gov-data-crawler
Property 2: contract detail URL is correctly constructed

Validates: Requirements 2.1
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from gov_data_crawler.listing import CONTRACT_DETAIL_URL_TEMPLATE


# Strategy: generate alphanumeric contract ID strings
alphanumeric_contract_id_strategy = st.text(
    alphabet=st.sampled_from(
        "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ),
    min_size=1,
    max_size=20,
)


@settings(max_examples=100, deadline=1000)
@given(contract_id=alphanumeric_contract_id_strategy)
def test_contract_detail_url_matches_expected_pattern(contract_id: str) -> None:
    """Property 2: For any alphanumeric contract ID string, the constructed
    detail page URL SHALL match the pattern
    https://contratos.comprasnet.gov.br/transparencia/contratos/{contract_id}
    exactly.

    **Validates: Requirements 2.1**
    """
    constructed_url = CONTRACT_DETAIL_URL_TEMPLATE.format(contract_id)
    expected_url = f"https://contratos.comprasnet.gov.br/transparencia/contratos/{contract_id}"

    assert constructed_url == expected_url
