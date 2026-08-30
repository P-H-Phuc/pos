from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosPaymentCashChange(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.PosOrder = cls.env["pos.order"]
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash Account Test",
                "code": "CHT0001",
                "account_type": "asset_cash",
            }
        )
        cls.bank_account = cls.env["account.account"].create(
            {
                "name": "Bank Account Test",
                "code": "BANKT01",
                "account_type": "asset_cash",
            }
        )
        cls.cash_journal = cls.env["account.journal"].create(
            {
                "name": "Cash Journal Test POS",
                "code": "CHT01",
                "type": "cash",
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal Test POS",
                "code": "BANKT01",
                "type": "bank",
                "default_account_id": cls.bank_account.id,
            }
        )
        # Create POS config
        cls.pos_config = cls.env["pos.config"].create(
            {
                "name": "POS Test Config",
                "journal_id": cls.cash_journal.id,
            }
        )
        cls.cash_method = cls.env["pos.payment.method"].create(
            {
                "name": "Cash Payment Method Test",
                "journal_id": cls.cash_journal.id,
            }
        )
        cls.credit_payment_method = cls.env["pos.payment.method"].create(
            {
                "name": "Credit Payment Method Test",
                "journal_id": cls.bank_journal.id,
                "is_credit": True,
            }
        )
        cls.pos_config.write(
            {
                "payment_method_ids": [
                    Command.set([cls.cash_method.id, cls.credit_payment_method.id])
                ]
            }
        )
        # Create product
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "type": "consu",
                "list_price": 100.0,
                "available_in_pos": True,
            }
        )
        # Create partner
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})

    @classmethod
    def create_pos_order(cls, amount):
        # Open session
        cls.pos_config.open_ui()
        # Create order
        order = cls.PosOrder.create(
            {
                "session_id": cls.pos_config.current_session_id.id,
                "partner_id": cls.partner.id,
                "lines": [
                    Command.create(
                        {
                            "product_id": cls.product.id,
                            "price_unit": amount,
                            "qty": 1,
                            "tax_ids": [],
                            "price_subtotal": amount,
                            "price_subtotal_incl": amount,
                        }
                    ),
                ],
                "amount_total": amount,
                "amount_tax": 0.0,
                "amount_paid": amount,
                "amount_return": 0.0,
            }
        )
        return order

    @classmethod
    def pay_pos_order(cls, order, payment_method, amount=None):
        amount = amount if amount is not None else order.amount_total
        context_make_payment = {
            "active_ids": order.ids,
            "active_id": order.id,
        }
        pos_make_payment = (
            cls.env["pos.make.payment"]
            .with_context(**context_make_payment)
            .create({"amount": amount, "payment_method_id": payment_method.id})
        )
        pos_make_payment.with_context(**context_make_payment).check()

    def test_partner_credit_amount_increase_after_refund(self):
        initial_credit = self.partner.credit_amount
        order_amount = 150.0
        # Create order
        pos_order = self.create_pos_order(order_amount)
        # Create the refund
        refund_action = pos_order.refund()
        refund_order = self.PosOrder.browse(refund_action["res_id"])
        self.pay_pos_order(refund_order, self.credit_payment_method)
        # Check that credit amount increased by order amount
        self.assertEqual(
            self.partner.credit_amount,
            initial_credit + order_amount,
            "Partner credit amount did not increase correctly after refund.",
        )

    def test_partner_credit_amount_decrease_after_payment(self):
        # Set initial credit amount
        initial_credit = 300.0
        self.partner.credit_amount = initial_credit
        order_amount = 120.0
        pos_order = self.create_pos_order(order_amount)
        self.pay_pos_order(pos_order, self.credit_payment_method)
        # Check that credit amount decreased by order amount
        self.assertEqual(
            self.partner.credit_amount,
            initial_credit - order_amount,
            "Partner credit amount did not decrease correctly after payment.",
        )

    def test_payment_with_cash_method(self):
        initial_credit = 300.0
        self.partner.credit_amount = initial_credit
        order_amount = 80.0
        # Create order and payment using cash payment method
        pos_order = self.create_pos_order(order_amount)
        self.pay_pos_order(pos_order, self.cash_method)
        # Check that credit amount remains unchanged
        self.assertEqual(
            self.partner.credit_amount,
            initial_credit,
            "Partner credit amount should not change when paying with cash method.",
        )

    def test_multiple_payments_credit_and_cash(self):
        initial_credit = 500.0
        self.partner.credit_amount = initial_credit
        order_amount = 200.0
        credit_payment_amount = 120.0
        cash_payment_amount = order_amount - credit_payment_amount
        # Create order
        pos_order = self.create_pos_order(order_amount)
        # Make payment with credit method
        self.pay_pos_order(pos_order, self.credit_payment_method, credit_payment_amount)
        # Make payment with cash method
        self.pay_pos_order(pos_order, self.cash_method, cash_payment_amount)
        # Check that credit amount decreased only by the credit payment amount
        self.assertEqual(
            self.partner.credit_amount,
            initial_credit - credit_payment_amount,
            "Partner credit amount did not decrease correctly after multiple payments.",
        )
