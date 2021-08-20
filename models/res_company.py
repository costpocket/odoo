import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError

logger = logging.getLogger(__name__)

class CpResCompany(models.Model):
  _inherit = 'res.company'

  costpocket_tax_ids = fields.Many2many(
    string='CostPocket preselected taxes',
    comodel_name='account.tax'
  )

  # @api.model
  # def _incoming_finvoice_tax_domain(self):
  #   domain = [
  #     ('type_tax_use', '=', 'purchase'),
  #     ('amount_type', '=', 'percent'),
  #     ('price_include', '=', False),
  #   ]
  #   if len(self) == 1:
  #     domain.append(('company_id', '=', self.id))
  #   return domain


  # @api.model
  # def _default_finvoice_taxes(self):
  #   TaxEnv = self.env['account.tax']
  #   if not len(self) == 1:
  #     return TaxEnv

  #   default_names = {
  #     'Purchase 0%',
  #     'Purchase 10%',
  #     'Purchase 14%',
  #     'Purchase 20%',
  #     'Purchase 21%',
  #     'Purchase 24%',
  #   }
  #   taxes = TaxEnv.search(self._incoming_finvoice_tax_domain())

  #   filtered = taxes.filtered(lambda tax: tax.name in default_names)
  #   return filtered