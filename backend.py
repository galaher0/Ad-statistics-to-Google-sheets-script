import browser_cookie3
import pickle
import pygsheets as ps
import re
import requests
import time
import yaml
from bs4 import BeautifulSoup
from datetime import date
from http.cookiejar import CookieJar
from loguru import logger
from os import path


class Backend:

	def __init__(self):
		self.path_to_config = path.join('..', 'config', 'backend_config.yml')
		self.config = self.load_config()

		self.gc = ps.authorize(client_secret=path.join('..', 'config', 'client_secret.json'))

		# We make sure in the GUI part that all necessary settings are made 
		if 'GS' in self.config:
			self.gs = self.gc.open_by_key(self.config['GS']['spreadsheet_id'])
			self.ws = self.gs.worksheet_by_title(self.config['GS']['sheet_name'])

		self.cj = self._get_cookies()
		self.today_date = date.today().strftime("%d.%m.%Y")
		self.current_month = date.today().strftime("%Y-%m")
		self.platforms = ['Вконтакте', 'Facebook', 'MyTarget']
		self.pf_task = {

			'Вконтакте': self.process_vk,
			'Facebook': self.process_fb,
			'MyTarget': self.process_mt
		}
		self.data_to_write = {}
		# Separate dict for user report
		self.result_data = {}

	def _get_cookies(self, ):
		'''Returns user's browser cookies'''
		'''From file for testing'''
		with open('cookies.pickle', 'rb') as f:
			load_list_cookies = pickle.load(f)
		cj = CookieJar()
		for i in load_list_cookies:
			cj.set_cookie(i)
		'''From Chrome database'''
		# cj = browser_cookie3.chrome()
		return cj

	def get_gs_config(self):
		if 'GS' in self.config:
			return self.config['GS']
		else:
			self.config.update({'GS': {}})
			return {}

	def get_gs_sheets_list(self, gs_id):
		try:
			self.gs = self.gc.open_by_key(gs_id)
			self.config['GS']['spreadsheet_id'] = gs_id
			return [i.title for i in self.gs.worksheets()]
		except Exception as e:
			logger.debug(e)
			return 'Error'

	def get_columns(self, sheet_name):
		self.config['GS']['sheet_name'] = sheet_name
		logger.debug(self.config['GS'])
		self.ws = self.gs.worksheet_by_title(sheet_name)
		self.columns = self.ws.get_row(1)
		return self.columns
		
	def send_column_choice(self, column_choice):
		self.config['GS']['columns'] = {}
		for i in column_choice:
			self.config['GS']['columns'][i] = {
				'name': column_choice[i],
				'column_number': self.columns.index(column_choice[i]) + 1
			}
		self.save_config()

	def gs_setting_complete(self):
		return 'GS' in self.config and {'spreadsheet_id', 'sheet_name', 'columns'} <= set(self.config['GS'])

	def get_pf_names(self):
		return self.platforms

	def get_cbr_usd_rate(self):
		'''Downloads current official USD conversion rate from Russia's
		Central Bank and returns a number with 4 floating points'''

		cbr = requests.get('http://www.cbr.ru/scripts/XML_daily.asp')
		soup = BeautifulSoup(cbr.content, 'xml')
		rate = float(soup.find('CharCode', text='USD').find_next_sibling('Value')\
			.string.replace(',','.'))
		logger.info(f'Курс ЦБ USD на {self.today_date}: {rate}')
		return rate

	def process_vk(self, campaigns):
		'''Collects AD statistics from VK using official API given user's input
		parameters'''

		logger.info("Отправка запроса в ВК")

		url = 'https://api.vk.com/method/ads.getStatistics'
		data = {}

		'''
		'data' model = {
			campaign ID: {
				indicator1: value,
				indicator2: value,
				...
			}
			...
		}
		'''

		for campaign in campaigns:

			request_data = {

				'account_id': self.config['Вконтакте']['vk_ad_account_id'],
				'ids_type': 'campaign',
				'ids': campaign['id'],
				'period': 'month' if campaign['period'] == 'Тек. месяц' else 'day',
				'date_from': 0 if campaign['period'] == 'Тек. месяц' 
								else campaign['dates'][0].strftime("%Y-%m-%d"),
				'date_to': self.current_month if campaign['period'] == 'Тек. месяц' 
								else campaign['dates'][1].strftime("%Y-%m-%d"),
				'access_token': self.config['Вконтакте']['vk_access_token'],
				'v': '5.124'

			}

			try:
				r = requests.get(url, params=request_data)
				logger.debug('GET WORKED')
			except:
				r = requests.post(url, data=request_data)
				logger.debug('POST WORKED')

			json_response = r.json()

			if "error" in json_response or \
			not len(json_response['response'][0]['stats']):
				logger.info("Ошибка запроса в ВК")
				logger.debug(json_response)
				return

			logger.debug(f'VK API response: {json_response}')

			# No campaigns on video views (at least for that client)
			# Two cases are handled: if month we're just collecting info from 
			# the response, if days it sums up indicators

			NA_list = []
			data[campaign['id']] = {}

			if campaign['period'] == 'Тек. месяц':
				for key in ['spent', 'impressions', 'clicks', 'reach']:
					if campaign[key]:
						if key in json_response['response'][0]['stats'][0]:
							data[campaign['id']][key] = json_response['response'][0]['stats'][0][key]
						else:
							NA_list.append(key)
				data[campaign['id']]['spent'] = float(data[campaign['id']]['spent'])
			else:
				for key in ['spent', 'impressions', 'clicks', 'reach']:
					if campaign[key]:
						if key in json_response['response'][0]['stats'][0]:
							data[campaign['id']][key] = json_response['response'][0]['stats'][0][key]
						else:
							NA_list.append(key)
				data[campaign['id']]['spent'] = float(data[campaign['id']]['spent'])

				for i in range(1, len(json_response['response'][0]['stats'])):
					try:
						for key in data[campaign['id']].keys():
							if key == 'spent':
								data[campaign['id']]['spent'] += \
								float(json_response['response'][0]['stats'][i][key])
							else:
								data[campaign['id']][key] += json_response['response'][0]['stats'][i][key]
					except:
							continue

				logger.info(f"Data returned from "
					f"{json_response['response'][0]['stats'][0]['day']} to "
					f"{json_response['response'][0]['stats'][-1]['day']}")

			logger.info(f'For ID {campaign["id"]} VK data extracted: '
				f'{data[campaign["id"]]}')
			if NA_list: logger.info(f'VK data not found: {NA_list}')
			logger.debug(f'VK DATA: {data}')
		
		self.data_to_write.update(data)
		self.result_data.update({'Вконтакте': data})

	def get_fb_creds(self):
		'''Gets FB access token and session_id'''

		logger.info("Request for FB access token and session id")
		r_auth = requests.get('https://business.facebook.com/adsmanager/\
			manage/campaigns', 
			headers=self.config['Facebook']['authorize']['headers'], 
			params=self.config['Facebook']['authorize']['params'], 
			cookies=self.cj)

		token_re = re.compile(r'window.__accessToken="(.*)";')
		token_search_result = re.search(token_re, r_auth.text)
		access_token = token_search_result.groups()[0] if token_search_result else None

		sessionID_re = re.compile(r'{"sessionID":"([a-z0-9]{16})"},')
		sessionID_search_result = re.search(sessionID_re, r_auth.text)
		session_id = sessionID_search_result.groups()[0] if sessionID_search_result else None

		return access_token, session_id

	def process_fb(self, campaigns):
		'''Collects active FB ad campaign statistics using Graph API according
		to clients' account IDs provided by user '''

		logger.info("Отправка запроса в Facebook")

		# Key translation dict
		translate = {
			'clicks': 'clicks',
			'impressions': 'impressions',
			'reach': 'reach',
			'spend': 'spent'
		}

		data = {}

		rate = self.get_cbr_usd_rate()

		for campaign in campaigns:

			# Modifying parameters and headers before the request
			self.config['Facebook']['get_campaign_data']['params'].update({

				'filtering': f'[{{"field":"campaign.delivery_info",'
				f'"operator":"IN","value":["active","archived","completed",'
				f'"inactive","limited","not_delivering","not_published",'
				f'"pending_review","permanently_deleted","recently_completed",'
				f'"recently_rejected","rejected","scheduled"]}},'
				f'{{"field":"campaign.id","operator":"IN",'
				f'"value":["{campaign["id"]}"]}}]',

				'time_range': f'{{"since":"{campaign["dates"][0]}",'
				f'"until":"{campaign["dates"][1]}"}}'

			})

			r = requests.get(f'https://graph.facebook.com/v7.0/'
				f'act_{campaign["client_id"]}/am_tabular',
				headers=self.config['Facebook']['get_campaign_data']['headers'],
				params=self.config['Facebook']['get_campaign_data']['params'])
			j = r.json()

			logger.debug(f'FB Graph response for CLIENT '
				f'{campaign["client_id"]} CAMPAIGN {campaign["id"]}: {j}')

			if 'error' in j and j['error']['code'] == 190:
				access_token, session_id = self.get_fb_creds()
				if all([access_token, session_id]):
					
					self.config['Facebook']['get_campaign_data']['params'].update({
						'access_token': access_token,
						'_sessionID': session_id
					})

					r = requests.get(f'https://graph.facebook.com/v7.0/'
						f'act_{campaign["client_id"]}/am_tabular',
						headers=self.config['Facebook']['get_campaign_data']['headers'],
						params=self.config['Facebook']['get_campaign_data']['params'])
					j = r.json()

				else:
					
					logger.info("Did not manage to get FB credentials")
					logger.debug(f'FB DATA: {data}')
		
					self.data_to_write.update(data)
					self.result_data.update({'Facebook': data})
					return 

			elif 'error' in j:
				
				logger.debug("Unknown error in FB server response")

			# Parsing response' json
			'''
			'data' model = {
				campaign ID: {
					indicator1: value,
					indicator2: value,
					...
				},
				...
			}
			'''
			try:
				data[j['data'][0]['rows'][0]['dimension_values'][0]] = {}
				for i in range(len(j['data'][0]['headers']['atomic_columns'])):
					data[
						j['data'][0]['rows'][0]['dimension_values'][0]
					][
						translate[ # Using program indicator names instead of FB native
							j['data'][0]['headers']['atomic_columns'][i]['name']
						]
					] = j['data'][0]['rows'][0]['atomic_values'][i]

				if j['data'][0]['rows'][0]['dimension_values'][3] == 'LINK_CLICKS':
					data[j['data'][0]['rows'][0]['dimension_values'][0]]['clicks'] = j['data'][0]['rows'][0]['result_values'][0]['value']

				elif j['data'][0]['rows'][0]['dimension_values'][3] == 'CONVERSIONS':
					data[j['data'][0]['rows'][0]['dimension_values'][0]]['result'] = j['data'][0]['rows'][0]['result_values'][0]['value']

				else:
					logger.debug(f"Unknown FB result target: {j['data'][0]['rows'][0]['dimension_values'][3]}")

				# for entry in j['data'][0]['rows']:
				# 	data[entry['dimension_values'][0]] = {}
				# 	data[entry['dimension_values'][0]]['result'] = \
				# 		entry['result_values'][0]['value']
				# 	for i in range(len(j['data'][0]['headers']['atomic_columns'])):
				# 		data[
				# 			entry['dimension_values'][0]
				# 		][
				# 			translate[ # Using universal keys instead of FB native
				# 				j['data'][0]['headers']['atomic_columns'][i]['name']
				# 			]
				# 		] = entry['atomic_values'][i]
			except Exception as e:
				logger.debug(f'Error occured while trying to parse this data: \n{e}')

			logger.info(f'For FB Client {campaign["client_id"]} CAMPAIGN '
				f'{campaign["id"]} the following data extracted: '
				f'{data[j["data"][0]["rows"][0]["dimension_values"][0]]}')

		for i in data:
			data[i]['spent'] = round(float(data[i]['spent']) * rate, 2)
			
		logger.debug(f'FB DATA: {data}')
		
		self.data_to_write.update(data)
		self.result_data.update({'Facebook': data})

	def process_mt(self, campaigns):
		'''Collects active MyTarget ad campaign statistics using json API according
		to clients' account IDs provided by user'''

		# Getting internal MT client ids
		client_internal_ids = {}

		for c in campaigns:
			if c['client_id'] not in client_internal_ids:

				self.config['MyTarget']['get_client_id']['params']['sudo'] = c['client_id']

				r = requests.get(
					'https://target.my.com/dashboard', 
					headers=self.config['MyTarget']['get_client_id']['headers'],
					params=self.config['MyTarget']['get_client_id']['params'], 
					cookies=self.cj
				)

				logger.debug(f'Got client id html: {[i for i in r.iter_lines()][2]}')

				soup = BeautifulSoup(r.text, features='lxml')
				client_int_id = soup.html['data-ga-userid']

				logger.debug(f"Got client id {client_int_id} for input ID {c['client_id']}")

				client_internal_ids[c['client_id']] = client_int_id

		# Getting data for each campaign
		data = {}
		'''
		'data' model = {
			campaign ID: {
				indicator1: value,
				indicator2: value,
				...
			},
			...
		}
		'''

		for c in campaigns:

			# Getting a list of currently active campaigns

			# self.config['MyTarget']['get_active_campaigns']['headers'].update(
			# 	{
			# 		'X-Target-Sudo': f"target.deltaclick@mail.ru,{c['client_id']}",
			# 		'Referer': f"https://target.my.com/dashboard?sudo="
			# 			f"target.deltaclick%40mail.ru%2C{c['client_id']}"
			# 	}
			# )
			# self.config['MyTarget']['get_active_campaigns']['params'].update(
			# 	{
			# 		'_user_id__in': client_internal_ids[c['client_id']],
			# 		'_': str(int(time.time() * 1000))
			# 	}
			# )

			# r = requests.get(
			# 	'https://target.my.com/api/v2/campaigns.json',
			# 	headers=self.config['MyTarget']['get_active_campaigns']['headers'], 
			# 	params=self.config['MyTarget']['get_active_campaigns']['params'], 
			# 	cookies=self.cj
			# )
			# j = r.json()

			# logger.debug(f'Got campaigns json: {j}')

			# campaigns = []
			# for i in j['items']:
			# 	if i['delivery'] == 'delivering':
			# 		campaigns.append(str(i['id']))

			'''For some reason during the active period campaigns can chnage 
			their status to idle. So, not to miss them we store them in config 
			and combine with future	responses'''

			# campaigns = self.union(campaigns, 
			# 						self.config['MyTarget']['cur_campaigns'])
			# self.config['MyTarget']['cur_campaigns'] = campaigns

			# logger.debug(f'Active campaigns: {campaigns}')
			# campaigns = ['34482609', '34482513', '34367165', '34367127', '34367104', '34367057']
			# limit = str(len(campaigns))

			# Getting ad data

			self.config['MyTarget']['get_ad_data']['headers'].update(
				{
					'X-Target-Sudo':  c['client_id'],
					'Referer': f"https://target.my.com/dashboard?sudo="
					f"{c['client_id']}"
				}
			)
			self.config['MyTarget']['get_ad_data']['params'].update(
				{
					'id': c['id'],
					'date_from': c['dates'][0].strftime("%d.%m.%Y"),
					'date_to': c['dates'][1].strftime("%d.%m.%Y"),
					'adv_user': client_internal_ids[c['client_id']],
					'_': str(int(time.time() * 1000))
				}
			)
			r = requests.get(
				'https://target.my.com/api/v3/statistics/campaigns/day.json', 
				headers=self.config['MyTarget']['get_ad_data']['headers'], 
				params=self.config['MyTarget']['get_ad_data']['params'], 
				cookies=self.cj
			)
			j = r.json()

			logger.debug(f'Got ad data json: {j}')
			if 'error' in j:
				logger.debug(f"MyTarget returned an error: {j['error']['code']}")
				# TO DO inform user about a problem
			else:
				for i in j['items']:
					data[i['id']] = {}
					data[i['id']]['impressions'] = i['total']['base']['shows']
					data[i['id']]['clicks'] = i['total']['base']['clicks']
					data[i['id']]['spent'] = i['total']['base']['spent']
					data[i['id']]['reach'] = i['total']['uniques']['increment']

		logger.info(f'MT DATA: {data}')
		
		self.data_to_write.update(data)
		self.result_data.update({'MyTarget': data})

	def write_to_gspread(self):
		'''Writes collected data to a specified Google Spreadsheet'''

		if 'campaign_rows' not in self.config['GS']:
			self.config['GS']['campaign_rows'] = {}

		# Storing campaign rows in GS to save traffic in the future
		for campaign_id in self.data_to_write:
			if campaign_id not in self.config['GS']['campaign_rows']:
				try:
					cells_list = self.ws.find(campaign_id)
				except Exception as e:
					logger.debug(f"During campaign id search the following error happened: \n{e}")
				if not cells_list:
					logger.debug(f"{campaign_id} not found in GS")
				else:
					self.config['GS']['campaign_rows'][campaign_id] = cells_list[0].row
		
		# Deleting no longer actual entries from config
		for campaign_id in set(self.config['GS']['campaign_rows']) - set(self.data_to_write):
			self.config['GS']['campaign_rows'].pop(campaign_id)

		# Updating values
		all_values = self.ws.get_all_values()
		for campaign_id in self.data_to_write:
			for indicator in self.data_to_write[campaign_id]:
				all_values[
						self.config['GS']['campaign_rows'][campaign_id]-1
					][
						self.config['GS']['columns'][indicator]['column_number']-1
					] = self.data_to_write[campaign_id][indicator]

			# Updating date values
			all_values[
					self.config['GS']['campaign_rows'][campaign_id]-1
				][
					self.config['GS']['columns']['date']['column_number']-1
				] = self.today_date

		self.ws.update_values(crange=(1,1), values=all_values, parse=True)

	def load_config(self):
		'''Loads configuration parameters'''
		logger.info('Call to load backend config')
		if path.exists(self.path_to_config):
			with open(self.path_to_config, 'r', encoding='utf-8') as y:
				conf = yaml.safe_load(y)
			logger.info(f'Config loaded')
			return conf
		logger.info('Returning empty config')
		return {}

	def save_config(self):
		'''Saves backend parameters to disk'''

		logger.info('Call to save config file')
		with open(self.path_to_config, 'w', encoding='utf-8') as f:
			yaml.dump(self.config, f, allow_unicode=True)
		logger.info('Input saved to disk')

	def get_result(self):
		return self.result_data

	def run(self, input_dict):
		'''Runs main backend process: parses ad platfoms and writes them
		to Google Spreadsheet'''

		for pf in input_dict:
			self.pf_task[pf](input_dict[pf])
		logger.info(f"Data to write to GS: {self.data_to_write}")
		self.write_to_gspread()
		self.save_config()


'''
class GoogleSpreadsheet:
	
	# If modifying these scopes, delete the file token.pickle.
	SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

	def __init__(self, spreadsheet_id, range_name):
		self.spreadsheet_id = spreadsheet_id
		self.range = range_name
		self._creds = self._get_creds()

	def _get_creds(self):
		"""
		The file token.pickle stores the user's access and refresh tokens, 
		and is created automatically when the authorization flow completes 
		for the first time.
		"""

		creds = None
		
		if os.path.exists('token.pickle'):
			with open('token.pickle', 'rb') as token:
				creds = pickle.load(token)

		# If there are no (valid) credentials available, let the user log in.
		if not creds or not creds.valid:
			if creds and creds.expired and creds.refresh_token:
				creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(
					'credentials.json', self.SCOPES)
				creds = flow.run_local_server(port=0)
			# Save the credentials for the next run
			with open('token.pickle', 'wb') as token:
				pickle.dump(creds, token)

		return creds

	def write(self, id_, data):

		service = build('sheets', 'v4', credentials=self._creds)

		# Call the Sheets API
		sheet = service.spreadsheets()
		result = sheet.values().get(spreadsheetId=self.spreadsheet_id,
								   range=self.range).execute()
		values = result.get('values', [])

		if not values:
			print('Данные не найдены.\n')
		else:
			print('Гугл таблица найдена\n')

		# Finding a row to write values using ad id
		id_column = [values[i][0] if values[i] else "" for i in range(len(values))]
		if id_ in id_column:
			no_row_to_write = id_column.index(id_)
		else:
			print("ID кампании не найден в Гугл таблице. Выход из программы.")
			exit(1)

		# Columns numbers are hardcoded
		columns_to_write = ['J', 'M', 'U', 'V', 'X']
		values_to_write = [i for i in data.values()]

		for i in range(len(values_to_write)):
			cell = columns_to_write[i] + f'{no_row_to_write+1}'
			body = {'values': [[values_to_write[i]]]}
			result = service.spreadsheets().values().update(
				spreadsheetId=self.spreadsheet_id, range=cell,
				valueInputOption='USER_ENTERED', body=body).execute()
			print('{} cell updated in the {} cell.'
				.format(result.get('updatedCells'), cell))
'''