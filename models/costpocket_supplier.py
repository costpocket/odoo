# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, fields, models, _

logger = logging.getLogger(__name__)



class FinvoiceProductMatch(models.Model):
    _name = "finvoice.product.match"
    _description = "Map product names to product id's, using wildcard matching"
    _order = 'sequence, id'

    sequence = fields.Integer(
        string="Sequence",
        default=10
    )

    name_match = fields.Char(
        string="Name mask",
        required=False,
        help="Define string mask for matching article names. "
            "Mask can be whole name of the product or any part of product name.",
    )

    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        required=False,
        string='Supplier',
        help="Define supplier for using this mask for only invoices for specified supplier. "
            "If name mask is empty, all invoices from specified supplier are mapped to the same product.",
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        string='Product'
    )

    company_id = fields.Many2one(
        related='product_id.company_id', readonly=True)

    def find_product(self, company_id, supplier_id, name):
        #  match can be found using either name mask, supplier id or combination of them.
        # note: empty mask matches every line using 'in' operand
        domain = [
            ('company_id', 'in', [company_id.id, False]),
            ('supplier_id', 'in', [supplier_id.id, False]),
        ]
        for match in self.search(domain):
            if re.findall(match.name_match, name):
                return match.product_id
