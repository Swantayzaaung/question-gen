from .arithmetic_series import ArithmeticSeriesTemplate
from .geometric_series import GeometricSeriesTemplate
from .differentiation import DifferentiationTemplate
from .integration import IntegrationTemplate
from .logarithms import LogarithmsTemplate
from .binomial_expansion import BinomialExpansionTemplate

TEMPLATE_MAP = {
    "arithmetic_series": ArithmeticSeriesTemplate,
    "geometric_series": GeometricSeriesTemplate,
    "differentiation": DifferentiationTemplate,
    "integration": IntegrationTemplate,
    "logarithms": LogarithmsTemplate,
    "binomial_expansion": BinomialExpansionTemplate,
}


def get_template(topic: str):
    cls = TEMPLATE_MAP.get(topic)
    return cls() if cls else None
