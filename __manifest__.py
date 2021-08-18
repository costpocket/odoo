# -*- coding: utf-8 -*-
{
    'name': "CostPocket",
    'summary': """
The easiest expense management app with OCR - CostPocket""",
    'description': """
CostPocket makes expense reporting easy! Unlike other expense apps we offer digitalization of receipts, you only have to make a picture.
    """,
    'author': "CostPocket",
    'website': "http://www.costpocket.com",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['base', 'web', 'account'],
    'data': [
        'views/res_config_settings_view.xml',
        'data/costpocket_cron_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
