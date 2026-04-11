from app.routes.expenses import _validate_amount, _validate_category
from app.constants import EXPENSE_CATEGORIES


class TestValidateAmount:
    def test_valid_amount(self):
        assert _validate_amount('100.50') == 100.50

    def test_zero_rejected(self):
        assert _validate_amount('0') is None

    def test_negative_rejected(self):
        assert _validate_amount('-50') is None

    def test_too_large_rejected(self):
        assert _validate_amount('99999999') is None

    def test_non_numeric_rejected(self):
        assert _validate_amount('abc') is None

    def test_none_rejected(self):
        assert _validate_amount(None) is None

    def test_max_boundary(self):
        assert _validate_amount('9999999.99') == 9999999.99

    def test_small_valid(self):
        assert _validate_amount('0.01') == 0.01


class TestValidateCategory:
    def test_valid_categories(self):
        for cat in EXPENSE_CATEGORIES:
            assert _validate_category(cat) == cat

    def test_invalid_defaults_to_miscellaneous(self):
        assert _validate_category('InvalidCat') == 'Miscellaneous'

    def test_empty_string(self):
        assert _validate_category('') == 'Miscellaneous'

    def test_case_sensitive(self):
        assert _validate_category('food') == 'Miscellaneous'
        assert _validate_category('Food') == 'Food'
