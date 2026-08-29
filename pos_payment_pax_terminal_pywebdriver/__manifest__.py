{
    "name": "POS Payment PAX (pywebdriver)",
    "version": "18.0.1.0.0",
    "category": "Point Of Sale",
    "summary": "Integrate PAX terminals with Odoo POS via a local pywebdriver proxy",
    "author": "Odoo Community Association (OCA), Trobz",
    "website": "https://github.com/OCA/pos",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/pos_payment_method_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payment_pax_terminal_pywebdriver/static/src/app/**/*",
            "pos_payment_pax_terminal_pywebdriver/static/src/overrides/**/*",
        ],
    },
    "installable": True,
}
