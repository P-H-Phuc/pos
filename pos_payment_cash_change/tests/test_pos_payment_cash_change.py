# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@tagged("post_install", "-at_install")
class TestPosPaymentCashChange(TestPointOfSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.change_account = cls.env["account.account"].create(
            {
                "name": "Cash Change Account",
                "code": "CCG001",
                "account_type": "asset_current",
            }
        )

    @classmethod
    def update_cash_payment_method(self, change_account):
        self.cash_payment_method.write(
            {
                "change_account_id": change_account.id,
            }
        )
        self.pos_config.write(
            {
                "payment_method_ids": [
                    Command.clear(),
                    Command.link(self.cash_payment_method.id),
                ]
            }
        )

    @classmethod
    def prepare_pos_order_vals(cls, session):
        return {
            "company_id": cls.env.company.id,
            "session_id": session.id,
            "partner_id": cls.partner1.id,
            "lines": [
                Command.create(
                    {
                        "product_id": cls.product3.id,
                        "qty": 1,
                        "price_subtotal": 100,
                        "price_subtotal_incl": 100,
                        "price_unit": 100,
                    },
                )
            ],
            "amount_total": 100,
            "amount_tax": 0,
            "amount_paid": 150,
            "amount_return": 50,
        }

    def test_condition_create_change_payment_move_cash_with_change_account(self):
        """Test condition for creating change payment move
        with cash and change account"""
        self.update_cash_payment_method(self.change_account)
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        order_vals = self.prepare_pos_order_vals(session)
        order = self.PosOrder.create(order_vals)
        self.assertTrue(
            order._condition_create_cash_change_payment_move(
                order_vals, order, session, False
            )
        )

    def test_condition_create_change_payment_move_cash_with_no_change_account(self):
        """Test condition for creating change payment move
        with cash and change account"""
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        order_vals = self.prepare_pos_order_vals(session)
        order = self.PosOrder.create(order_vals)
        self.assertFalse(
            order._condition_create_cash_change_payment_move(
                order_vals, order, session, False
            )
        )

    def test_process_cash_change_payments(self):
        self.update_cash_payment_method(self.change_account)
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        order_vals = self.prepare_pos_order_vals(session)
        order_vals.update(
            {
                "payment_ids": [
                    Command.create(
                        {
                            "payment_method_id": self.cash_payment_method.id,
                            "name": fields.Datetime.now(),
                            "amount": 150,
                        }
                    ),
                ],
                "date_order": fields.Datetime.to_string(fields.Datetime.now()),
                "fiscal_position_id": False,
                "name": "Order 12345-123-1234",
                "sequence_number": 2,
                "uuid": "12345-123-1234",
                "last_order_preparation_change": "{}",
                "user_id": self.env.uid,
                "state": "paid",
            }
        )
        self.PosOrder.sync_from_ui([order_vals])
        moves = self.env["account.move"].search(
            [
                ("partner_id", "=", self.partner1.id),
                ("ref", "like", "(Cash Change) Order Number"),
            ]
        )
        self.assertEqual(len(moves), 3)
