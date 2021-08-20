# -*- coding: utf-8 -*-
import logging
import requests
import json
import base64

from odoo import fields, models, api, _, _lt
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CP_API_S2S_BASEURL = 'https://api.costpocket.com/s2s'
CP_API_VERSION = 'v1'
CP_API_TIMEOUT = 10

class CostPocketAccount(models.Model):
  _inherit = 'account.move'
  
  cp_id = fields.Integer(string='CostPocket id')
  cp_company_paid = fields.Boolean(string='Paid by company')

  # finvoice_filename = fields.Char(
  #     'finvoice filename', compute='_compute_finvoice_filename')

class CostPocketAccount(models.Model):
  _inherit = 'account.account'

  # def _get_finvoice_taxes(self):
  #   self.ensure_one()
  #   tax_codes = self.env['account.tax']

  #   if self.finvoice_vat_rate_percent:
  #       domain = self.company_id._incoming_finvoice_tax_domain()
  #       domain.append(('amount', '=', float(self.finvoice_vat_rate_percent)))
  #       tax_codes = tax_codes.search(domain)
  #       # Try to use default tax code
  #       def_tax_code = tax_codes.filtered(
  #           lambda tax: tax in self.company_id.incoming_finvoice_tax_ids)
  #       if def_tax_code:
  #           return def_tax_code[0]
  #       if tax_codes:
  #           return tax_codes[0]

  #   return tax_codes

  @api.model
  def _fetch_costpocket_expenses(self):
    ''' COSTPOCKET expenses cron job '''

    request_url = 'https://api.costpocket.com/s2s/v1/expenses/documents?status=!received'
    success_url = 'https://api.costpocket.com/s2s/v1/expenses/documents/status'

    params = self.env['ir.config_parameter'].sudo()

    api_is_active = params.get_param('costpocket_api_is_active')
    api_token = params.get_param('costpocket_api_token')
    api_bcx = params.get_param('costpocket_api_bcx')
    api_id = params.get_param('costpocket_api_id')

    if api_is_active and api_id and api_token:
      
      try:
        active_request = requests.get(
          url = request_url,
          headers = {
            'api-id': api_id,
            'api-token': api_token,
          },
          timeout = CP_API_TIMEOUT,
        )

        active_request.raise_for_status()
        response = active_request.json()

        success_ids = []

        for document in response:         
          _logger.info('Adding new CP document', document)

          currency_id = self.env['res.currency'].search([ 
            ['name', '=', document['information']['currency'] or 'EUR']
          ])

          account_id = self.env['account.account'].search([
            ('company_id', '=', self.env.user.company_id.id),
            ('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)
          ], limit=1)

          partner_id = self.env.user.partner_id
          cp_company_paid = False

          if document['metadata']['billingType'] == 'company':
            cp_company_paid = True

            if document['supplier']['regCode'] or document['supplier']['VATNumber']:
              partner_id = self.env['res.partner'].search([
                ['vat', '=', document['supplier']['VATNumber']]
              ], limit=1)

              if not partner_id:
                partner_id = self.env['res.partner'].sudo().create({
                  'name': document['supplier']['name'],
                  'vat': document['supplier']['VATNumber'],
                })
          
          else:
            partner_id = self.env['res.partner'].search([
              ['vat', '=', document['submitter']['email']]
            ], limit=1)

          document_payload = {
            'cp_company_paid': cp_company_paid,
            'partner_id': partner_id.id,
            'cp_id': document['id'],
            'move_type': 'in_invoice',
            'date': document['createdAt'],
            'invoice_date': document['createdAt'],
            'currency_id': currency_id.id,
            'date': document['information']['issued'],
            'invoice_line_ids': []
          }

          for row in document['itemRows']:
            tax_id = None

            tax_ids = self.env['account.tax'].search([
              ('company_id', '=', self.env.user.company_id.id),
              ('type_tax_use', '=', 'purchase'),
              ('amount_type', '=', 'percent'),
              ('price_include', '=', False),
              ('amount', '=', float(row['VATrate']))
            ])

            cp_tax_ids = tax_ids.filtered(lambda tax: tax in self.env.user.company_id.costpocket_tax_ids)

            if cp_tax_ids:
              tax_id = cp_tax_ids[0]

            elif tax_ids:
              tax_id = tax_ids[0]

            document_payload['invoice_line_ids'] += [(0, None, {
              'quantity': row['quantity'],
              'name': row['description'] or '----',
              'price_unit': row['price'],
              'currency_id': currency_id.id,
              'account_id': account_id.id,
              'tax_ids': tax_id
            })]

          account_move = self.env['account.move'].sudo().with_context(check_move_validity=False).create(document_payload)

          if document['metadata']['billingType'] == 'company':
            account_move.line_ids.reconcile()

          if document['attachment']:
            base64_img_bytes = document['attachment']['content'].encode('utf-8')

            self.env['ir.attachment'].sudo().create({
                'name': document['attachment']['name'],
                'res_model': account_move._name,
                'res_id': account_move.id,
                'datas': base64.b64encode(base64_img_bytes),
                'type': 'binary',
            })

          success_ids += [{
            'documentId': document['id'],
            'reference': f'odoo-id={account_move.id}',
            'received': True
          }]

        if len(response) == 0:
          _logger.info('No new documents found')

        else:
          success_json = json.dumps(success_ids)

          success_status_request = requests.put(
            url = success_url,
            headers = {
              'api-id': api_id,
              'api-token': api_token,
            },
            data = success_json
          )

          success_status_request.raise_for_status()
          success_docs_count = len(success_ids)

          _logger.info(f'Successfully transferred {success_docs_count} documents')
          _logger.info(success_json)

            
      except requests.HTTPError as error:
        error_message = f'ERROR: {error}'
        _logger.info(error_message)
        raise UserError(error_message)

      except IOError:
        _logger.info('We failed to reach a CostPocket server.', exc_info=True)
        raise UserError(_('Internet connection failed'))

      except Exception as error:
        _logger.info(f'Something went wrong | {error}', exc_info=True)
        raise UserError(_('Something went wrong'))
