from app.utils import parse_sms, parse_receipt


class TestParseSms:
    def test_basic_upi_sms(self):
        text = "Rs.450 spent via UPI at Dominos on 2026-03-15"
        result = parse_sms(text)
        assert result['amount'] == 450.0
        assert result['date'] == '2026-03-15'
        assert result['payment_type'] == 'UPI'

    def test_inr_format(self):
        text = "INR 1200.50 debited from your account at Amazon"
        result = parse_sms(text)
        assert result['amount'] == 1200.50
        assert 'Amazon' in result['merchant']

    def test_rupee_symbol(self):
        text = "₹500 paid to Uber via card"
        result = parse_sms(text)
        assert result['amount'] == 500.0
        assert result['payment_type'] == 'Card'
        assert result['category'] == 'Transport'

    def test_food_category_detection(self):
        text = "Rs.200 at restaurant via UPI on 2026-01-10"
        result = parse_sms(text)
        assert result['category'] == 'Food'

    def test_shopping_category_detection(self):
        text = "Rs.3000 at Flipkart for shopping on 2026-02-20"
        result = parse_sms(text)
        assert result['category'] == 'Shopping'

    def test_no_date_defaults_to_today(self):
        text = "Rs.100 at store"
        result = parse_sms(text)
        assert result['date']  # should default to today
        assert len(result['date']) == 10  # YYYY-MM-DD format

    def test_dd_mm_yyyy_date_format(self):
        text = "Transaction on 15/03/2026 for Rs.500"
        result = parse_sms(text)
        assert result['date'] == '15-03-2026'

    def test_fallback_amount_largest_number(self):
        text = "Transaction 12345 completed for 500.00 items 3"
        result = parse_sms(text)
        assert result['amount'] == 12345.0


class TestParseReceipt:
    def test_basic_receipt(self):
        text = "Store: Pizza Hut\nDate: 2026-03-10\n₹350.00\nCard Payment"
        result = parse_receipt(text)
        assert result['amount'] == 350.0
        assert result['payment_type'] == 'Card'

    def test_merchant_from_first_line(self):
        text = "ACME Corp\nSome items\n$50.00"
        result = parse_receipt(text)
        assert result['merchant'] == 'ACME Corp'

    def test_merchant_from_store_line(self):
        text = "Receipt\nStore: Big Bazaar\nAmount: Rs.1500"
        result = parse_receipt(text)
        assert result['merchant'] == 'Big Bazaar'

    def test_food_category_from_merchant(self):
        text = "Dominos Pizza\n₹400\nUPI"
        result = parse_receipt(text)
        assert result['category'] == 'Food'

    def test_transport_category(self):
        text = "Uber Trip\n₹200\nUPI"
        result = parse_receipt(text)
        assert result['category'] == 'Transport'

    def test_upi_payment_type(self):
        text = "Store XYZ\n₹100\nPaid via UPI"
        result = parse_receipt(text)
        assert result['payment_type'] == 'UPI'
