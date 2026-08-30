{
    "name": "POS Payment PAX Terminal",
    "version": "18.0.1.0.0",
    "category": "Point Of Sale",
    "summary": "Integrate PAX payment terminals with Odoo POS via POS Link HTTP",
    "author": "Wokwy, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/pos",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/pax_terminal_views.xml",
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payment_pax_terminal_direct/static/src/app/**/*",
        ],
    },
    "installable": True,
}
