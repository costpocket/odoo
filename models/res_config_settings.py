# -*- coding: utf-8 -*-
import requests
import logging
import random
import secrets
import datetime

from odoo import fields, models, api, _, _lt
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CP_API_INTEGRATIONS_BASEURL = 'https://api.costpocket.com/integrations'
CP_API_VERSION = 'v1'
CP_API_TIMEOUT = 10

def genBCX():
  return secrets.token_urlsafe(24)

class ResConfigSettings(models.TransientModel):
  _inherit = 'res.config.settings'

  costpocket_api_is_active = fields.Boolean(string='Use CostPocket expense documents', default=False)
  costpocket_api_email = fields.Char(string='CostPocket API email', readonly=True)
  costpocket_api_token = fields.Char(string='CostPocket API token')
  costpocket_api_bcx = fields.Char(string='CostPocket API bcx')
  costpocket_api_id = fields.Char(string='CostPocket API id')

  costpocket_tax_ids = fields.Many2many(
    related='company_id.costpocket_tax_ids',
    readonly=False,
  )

  def _activate_cp(self):
    try:
      partner_id = self.env.user.partner_id
      company_id = self.env.user.company_id
      name_formatted = partner_id.name.rsplit(' ', 1)
      firstname = name_formatted[0] if len(name_formatted) > 0 else 'Unknow'
      lastname = name_formatted[1] if len(name_formatted) == 2 else firstname
      parameters = self.env['ir.config_parameter'].sudo()

      bcx = self.costpocket_api_bcx or genBCX()

      company_data = {
        "user":{
          "firstName": firstname,
          "lastName": lastname,
          "email": partner_id.email,
          "lang": "eng"
        },
        "company":{
          "bcx": bcx,
          "name": company_id.name,
          "regCode": company_id.company_registry,
          "VATAccountable": True if company_id.vat else None,
          "countryCode": company_id.country_code,
          "address": (company_id.street or '') + '' + (company_id.street2 or ''),
          "city": company_id.city,
          "zip": company_id.zip,
          "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        } 
      }

      _logger.info(f'Activationg company {company_data}')

      request_url = f'{ CP_API_INTEGRATIONS_BASEURL }/{ CP_API_VERSION }/partner/odoo/subscribe'
      
      active_request = requests.post(
        url = request_url,
        json = company_data,
        timeout = CP_API_TIMEOUT,
        headers = {'Environment': 'pro'}
      )

      active_request.raise_for_status()
      response = active_request.json()

      api_user = response.get('apiUser')
      api_bcx = bcx

      api_token = api_user['apiToken']
      api_id = api_user['apiId']

      api_email = partner_id.email

      if api_user and api_id and api_token and api_bcx and api_email:
        _logger.info(f'Costpocket activation. API TOKEN={api_token} | API ID={api_id} | API BCX={api_bcx} | API EMAIL={api_email}')
  
        parameters.set_param('costpocket_api_is_active', True)
        parameters.set_param('costpocket_api_token', api_token)
        parameters.set_param('costpocket_api_email', api_email)
        parameters.set_param('costpocket_api_bcx', api_bcx)
        parameters.set_param('costpocket_api_id', api_id)

      else:
        raise UserError(_(f'Missing data. API TOKEN={api_token} | API ID={api_id} | API BCX={api_bcx} | API EMAIL={api_email}'))

    except requests.exceptions.HTTPError as error:
      _logger.info(error)
      response = error.response.json()

      if response['message']:
        message = response['message'] if response['message'] else 'error'
        codename = response['codename'] if response['codename'] else 'undefined'

        raise UserError(f'{message} - [{codename}]')

    except Exception as error:
      _logger.info(f'Something went wrong | {error}', exc_info=True)
      raise UserError(error)
      

  def _deactivate_cp(self):
    set_param = self.env['ir.config_parameter'].sudo().set_param

    set_param('costpocket_api_is_active', False)
    set_param('costpocket_api_token', False)
    set_param('costpocket_api_email', False)
    set_param('costpocket_api_bcx', False)
    set_param('costpocket_api_id', False)

    _logger.info(f'CostPocket Deactivated')


  @api.model
  def get_values(self):
    response = super(ResConfigSettings, self).get_values()
    get_param = self.env['ir.config_parameter'].sudo().get_param

    payload = {
      "costpocket_api_is_active": get_param('costpocket_api_is_active'),
      "costpocket_api_token": get_param('costpocket_api_token'),
      "costpocket_api_email": get_param('costpocket_api_email'),
      "costpocket_api_bcx": get_param('costpocket_api_bcx'),
      "costpocket_api_id": get_param('costpocket_api_id')
    }

    response.update(payload)

    return response


  def set_values(self):
    res = super(ResConfigSettings, self).set_values()
    set_param = self.env['ir.config_parameter'].sudo().set_param

    set_param('costpocket_api_is_active', self.costpocket_api_is_active)
    set_param('costpocket_api_token', self.costpocket_api_token)
    set_param('costpocket_api_email', self.costpocket_api_email)
    set_param('costpocket_api_bcx', self.costpocket_api_bcx)
    set_param('costpocket_api_id', self.costpocket_api_id)

    if self.costpocket_api_is_active:
      self._activate_cp()

    elif not self.costpocket_api_is_active:
      self._deactivate_cp()

    return res
