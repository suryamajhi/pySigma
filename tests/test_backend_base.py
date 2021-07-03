from sigma.collection import SigmaCollection
from sigma.backends.base import TextQueryBackend
from sigma.processing.pipeline import ProcessingPipeline, ProcessingItem
from sigma.processing.transformations import FieldMappingTransformation, QueryExpressionPlaceholderTransformation
from sigma.types import SigmaCompareExpression
from sigma.exceptions import SigmaTypeError
from typing import ClassVar, Dict
import pytest

class TextQueryTestBackend(TextQueryBackend):
    group_expression : ClassVar[str] = "({expr})"

    or_token : ClassVar[str] = "or"
    and_token : ClassVar[str] = "and"
    not_token : ClassVar[str] = "not"
    eq_token : ClassVar[str] = "="

    str_quote : ClassVar[str] = '"'
    escape_char : ClassVar[str] = "\\"
    wildcard_multi : ClassVar[str] = "*"
    wildcard_single : ClassVar[str] = "?"
    add_escaped : ClassVar[str] = ":"
    filter_chars : ClassVar[str] = "&"

    re_expression : ClassVar[str] = "{field}=/{regex}/"
    re_escape_char : ClassVar[str] = "\\"
    re_escape : ClassVar[str] = ("/", "bar")

    cidrv4_expression : ClassVar[str] = "{field}={value}"
    cidrv4_in_list_expression : ClassVar[str] = "{field} in ({list})"
    cidrv4_wildcard : ClassVar[str] = None
    
    compare_op_expression : ClassVar[str] = "{field}{operator}{value}"
    compare_operators : ClassVar[Dict[SigmaCompareExpression.CompareOperators, str]] = {
        SigmaCompareExpression.CompareOperators.LT  : "<",
        SigmaCompareExpression.CompareOperators.LTE : "<=",
        SigmaCompareExpression.CompareOperators.GT  : ">",
        SigmaCompareExpression.CompareOperators.GTE : ">=",
    }

    field_null_expression : ClassVar[str] = "{field} is null"

    field_in_list_expression : ClassVar[str] = "{field} in ({list})"
    list_separator : ClassVar[str] = ", "

    unbound_value_str_expression : ClassVar[str] = '_="{value}"'
    unbound_value_num_expression : ClassVar[str] = '_={value}'
    unbound_value_re_expression : ClassVar[str] = '_=/{value}/'
    unbound_value_cidrv4_expression : ClassVar[str] = '_={value}'
    unbound_list_cidrv4_expression : ClassVar[str] = "_ in ({list})"

    backend_processing_pipeline = ProcessingPipeline([
        ProcessingItem(FieldMappingTransformation({
            "fieldA": "mappedA",
        }))
    ])

@pytest.fixture
def test_backend():
    return TextQueryTestBackend(
        ProcessingPipeline([
            ProcessingItem(FieldMappingTransformation({
                "fieldB": "mappedB",
            }))
        ]),
        testparam="testvalue",
    )

def test_init_processing_pipeline(test_backend):
    assert test_backend.processing_pipeline == ProcessingPipeline([
        ProcessingItem(FieldMappingTransformation({
            "fieldA": "mappedA",
        })),
        ProcessingItem(FieldMappingTransformation({
            "fieldB": "mappedB",
        })),
    ])

def test_init_config(test_backend):
    assert test_backend.config == { "testparam": "testvalue" }

def test_convert_value_str(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA: value
                condition: sel
        """)
    ) == ['mappedA="value"']

def test_convert_value_num(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA: 123
                condition: sel
        """)
    ) == ['mappedA=123']

def test_convert_value_null(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA: null
                condition: sel
        """)
    ) == ['mappedA is null']

def test_convert_query_expr():
    pipeline = ProcessingPipeline([
        ProcessingItem(QueryExpressionPlaceholderTransformation(expression="{field} in list({id})"))
    ])
    backend = TextQueryTestBackend(pipeline)
    assert backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|expand: "%test%"
                condition: sel
        """)
    ) == ['mappedA in list(test)']

def test_convert_query_expr_unbound():
    pipeline = ProcessingPipeline([
        ProcessingItem(QueryExpressionPlaceholderTransformation(expression="_ in list({id})"))
    ])
    backend = TextQueryTestBackend(pipeline)
    assert backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    "|expand": "%test%"
                condition: sel
        """)
    ) == ['_ in list(test)']

def test_convert_value_regex(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|re: pat.*tern/foobar
                condition: sel
        """)
    ) == ['mappedA=/pat.*tern\\/foo\\bar/']

def test_convert_value_regex_unbound(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    "|re": pat.*tern/foobar
                condition: sel
        """)
    ) == ['_=/pat.*tern\\/foo\\bar/']

def test_convert_value_cidr_wildcard_none(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|cidrv4: 192.168.0.0/14
                condition: sel
        """)
    ) == ['mappedA=192.168.0.0/14']


def test_convert_value_cidr_wildcard_asterisk(test_backend):
    my_backend = test_backend
    my_backend.cidrv4_wildcard = "*"
    assert my_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|cidrv4: 192.168.0.0/14
                condition: sel
        """)
    ) == ['mappedA in ("192.168.*", "192.169.*", "192.170.*", "192.171.*")']

def test_convert_value_cidr_wildcard_none_unbound(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    "|cidrv4": 192.168.0.0/14
                condition: sel
        """)
    ) == ['_=192.168.0.0/14']

def test_convert_value_cidr_wildcard_asterisk_unbound(test_backend):
    my_backend = test_backend
    my_backend.cidrv4_wildcard = "*"
    assert my_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    "|cidrv4": 192.168.0.0/14
                condition: sel
        """)
    ) == ['_ in ("192.168.*", "192.169.*", "192.170.*", "192.171.*")']

def test_convert_compare(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|lt: 123
                    fieldB|lte: 123
                    fieldC|gt: 123
                    fieldD|gte: 123
                condition: sel
        """)
    ) == ['mappedA<123 and mappedB<=123 and fieldC>123 and fieldD>=123']

def test_convert_compare_str(test_backend):
    with pytest.raises(SigmaTypeError, match="incompatible to value type"):
        test_backend.convert(
            SigmaCollection.from_yaml("""
                title: Test
                status: test
                logsource:
                    category: test_category
                    product: test_product
                detection:
                    sel:
                        fieldA|lt: test
                    condition: sel
            """))

def test_convert_value_in_list(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA:
                        - value1
                        - value2
                        - value3
                condition: sel
        """)
    ) == ['mappedA in ("value1", "value2", "value3")']

def test_convert_unbound_values(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    - value1
                    - value2
                    - 123
                condition: sel
        """)
    ) == ['_="value1" or _="value2" or _=123']

def test_convert_and(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel1:
                    fieldA: value1
                sel3:
                    fieldC: value3
                condition: sel1 and sel3
        """)
    ) == ['mappedA="value1" and fieldC="value3"']

def test_convert_or(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel1:
                    fieldA: value1
                sel3:
                    fieldC: value3
                condition: sel1 or sel3
        """)
    ) == ['mappedA="value1" or fieldC="value3"']

def test_convert_not(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA: value1
                condition: not sel
        """)
    ) == ['not mappedA="value1"']

def test_convert_precedence(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel1:
                    fieldA: value1
                sel2:
                    fieldB: value2
                sel3:
                    fieldC: value3
                sel4:
                    fieldD: value4
                condition: (sel1 or sel2) and not (sel3 and sel4)
        """)
    ) == ['(mappedA="value1" or mappedB="value2") and not (fieldC="value3" and fieldD="value4")']

def test_convert_multi_conditions(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel1:
                    fieldA: value1
                sel3:
                    fieldC: value3
                condition:
                    - sel1
                    - sel3
        """)
    ) == ['mappedA="value1"', 'fieldC="value3"']

def test_convert_list_cidr_wildcard_none(test_backend):
    assert test_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|cidrv4: 
                        - 192.168.0.0/14
                        - 10.10.10.0/24
                condition: sel
        """)
    ) == ['mappedA=192.168.0.0/14 or mappedA=10.10.10.0/24']

def test_convert_list_cidr_wildcard_asterisk(test_backend):
    my_backend = test_backend
    my_backend.cidrv4_wildcard = "*"
    assert my_backend.convert(
        SigmaCollection.from_yaml("""
            title: Test
            status: test
            logsource:
                category: test_category
                product: test_product
            detection:
                sel:
                    fieldA|cidrv4: 
                        - 192.168.0.0/14
                        - 10.10.10.0/24
                condition: sel
        """)
    ) == ['mappedA in ("192.168.*", "192.169.*", "192.170.*", "192.171.*") or mappedA="10.10.10.*"']   