import requests
import unicodedata
import re
from argparse import ArgumentParser
from pathlib import Path
from bs4 import BeautifulSoup

class LeaCountyIndexer:
    def __init__(self) -> None:
        self.instruments = []
        self.instrument_urls = set()
        self.args = self._get_args()
        self.run()

    
    def run(self):
        if self.args.grantor or self.args.both:
            self.set_instrument_urls(name=self.args.name, date=self.args.date, page="optGrantor")
        if self.args.grantee or self.args.both:
            self.set_instrument_urls(name=self.args.name, date=self.args.date, page="optGrantee")
        
        for url in self.instrument_urls:
            self.add_instrument_data(url)

        self.create_html(path=self.args.output, descending=self.args.descending)


    
    def set_instrument_urls(self, name: str, date: str, page: str) -> None:
        next_url = ""
        host = "http://liveweb.leacounty-nm.org/"
        search_template = host + 'clerk.aspx?source=clerk&page={page}'
        data = {
            'searchTerm': name,
            'filedte': date,
            'docs': 'ALL'
        }

        while(True):
            try:
                if not next_url:
                    req = requests.post(url = search_template.format(page = page), data = data)
                else:
                    req = requests.get(next_url)
                soup = BeautifulSoup(req.content, 'html.parser')
                data_table = soup.find(attrs={'id': 'pagecontent'}).find_all('table')[-1]
            except IndexError:
                return
            else: 
                # add urls from data table to doc_urls
                for row in data_table.find_all('tr')[1:]:
                    link = row.find_all('td')[-1].find('a').attrs['href'].replace(" ", "+")
                    self.instrument_urls.add(host + link)

                # set next url
                try:
                    next_url = host + data_table.nextSibling.attrs['href']
                except AttributeError:
                    return

    def add_instrument_data(self, url) -> None:
        req = requests.get(url)
        soup = BeautifulSoup(req.content, 'html.parser')
        
        # need to get data from each fieldset:
        #   Reception Information
        #   Grantee Information
        #   Grantor Information
        #   Description Information
        #   Legal Description

        instrument_data = {
            'reception_number': '',
            'instrument_type': '',
            'recording_type': '',
            'book': '',
            'page': '',
            'num_pages': '',
            'file_date': '',
            'instrument_date': '',
            'grantors': [],
            'grantees': [],
            'description': [],
            'legals': []
        }

        fieldsets = soup.find_all('fieldset')
        for fieldset in fieldsets:
            field_type = fieldset.find('h4').text.strip()
            if re.match("reception", field_type, flags=re.IGNORECASE):
                # add reception information to instrument_data
                for label_el in fieldset.find_all('label'):
                    label = label_el.text
                    item = label_el.parent.nextSibling.strip() if label_el.parent.nextSibling.strip() != "" else label_el.parent.nextSibling.nextSibling.strip()

                    if re.match('reception.*', label, flags=re.IGNORECASE):
                        instrument_data['reception_number'] = item
                    elif re.match('kind.*', label, flags=re.IGNORECASE):
                        instrument_data['instrument_type'] = item
                    elif re.match('recording.*', label, flags=re.IGNORECASE):
                        instrument_data['recording_type'] = item
                    elif re.match('book.*', label, flags=re.IGNORECASE):
                        instrument_data['book'] = item
                    elif re.match('page.*', label, flags=re.IGNORECASE):
                        instrument_data['page'] = item
                    elif re.match('#.*', label, flags=re.IGNORECASE):
                        instrument_data['num_pages'] = item
                    elif re.match('date f.*', label, flags=re.IGNORECASE):
                        instrument_data['file_date'] = item
                    elif re.match('instrument.*|intrument.*', label, flags=re.IGNORECASE):
                        instrument_data['instrument_date'] = item
                    else:
                        print(label, item)


            elif re.match("grantee|grantor", field_type, flags=re.IGNORECASE):
                # add grantors and grantees to instrument_data
                names = [name.strip() for name in fieldset.text.split(r'&nbsp')[1:]]
                if re.match("grantor", field_type, flags=re.IGNORECASE):
                    instrument_data['grantors'] = names
                elif re.match("grantee", field_type, flags=re.IGNORECASE):
                    instrument_data['grantees'] = names



            elif re.match("description", field_type, flags=re.IGNORECASE):
                desc = [d.strip() for d in fieldset.text.split(r'&nbsp')[1:]]
                instrument_data['description'] = desc

            elif re.match("legal", field_type, flags=re.IGNORECASE):
                tracts = fieldset.get_text().replace("Legal Description", "").split("         ")
                instrument_data['legals'] = [unicodedata.normalize("NFKD", tract).strip() for tract in tracts if tract.strip() != ""]

        self.instruments.append(instrument_data)

    def create_html(self, path, descending):

        html_template = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="X-UA-Compatible" content="ie=edge">
                <title>{tab_title}</title>
                <style>
                    table.minimalistBlack {{
                        border: 3px solid #000000;
                        width: 100%;
                        text-align: left;
                        border-collapse: collapse;
                    }}

                    table.minimalistBlack td, table.minimalistBlack th {{
                        border: 1px solid #000000;
                        padding: 5px 4px;
                    }}

                    table.minimalistBlack tbody td {{
                        font-size: 13px;
                    }}

                    table.minimalistBlack thead {{
                        background: #CFCFCF;
                        background: -moz-linear-gradient(top, #dbdbdb 0%, #d3d3d3 66%, #CFCFCF 100%);
                        background: -webkit-linear-gradient(top, #dbdbdb 0%, #d3d3d3 66%, #CFCFCF 100%);
                        background: linear-gradient(to bottom, #dbdbdb 0%, #d3d3d3 66%, #CFCFCF 100%);
                        border-bottom: 3px solid #000000;
                    }}   

                    table.minimalistBlack thead th {{
                        font-size: 15px;
                        font-weight: bold;
                        color: #000000;
                        text-align: left;
                    }}

                    table.minimalistBlack tfoot td {{
                        font-size: 14px;
                    }}
                </style>
            </head>
            <body>
                <h1>{page_title}<h1>
                <table class="minimalistBlack">
                    <thead>
                        {headers}
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </body>
        </html>
        """

        self.instruments = sorted(self.instruments, key=lambda x: x['file_date'], reverse=self.args.descending)

        headers = list(self.instruments[0].keys())
        html_headers = "\n".join([f"<th>{header}</th>" for header in headers])

        html_rows = ""
        for row in self.instruments:
            html_rows += "<tr>"
            for header in headers:
                data = row[header]
                if type(data) == list:
                    html_rows += f"<td>{"</br>".join(data)}</td>"
                else:
                    html_rows += f"<td>{row[header]}</td>"
            html_rows += "</tr>"

        page_title = f"<h2>Index for: {self.args.name}</h2><h3>"
        if self.args.both:
            page_title += "Grantor and Grantee"
        elif self.args.both or self.args.grantor:
            page_title += "Grantor"
        elif self.args.grantee or self.args.grantee:
            page_title += "Grantee"
        page_title += "</h3>"
        if self.args.date:
            page_title += f"<h3>From {self.args.date} forward</h3>"
        else:
            page_title += f"<h3>All dates</h3>"
        

        with open(self.args.output, 'w') as output_file:
            output_file.write(html_template.format(tab_title=f"Lea County Index", page_title=page_title, headers=html_headers, rows=html_rows))
            output_file.close()

    def _get_args(self):
        self.parser = ArgumentParser(epilog='Example: lea-county-indexer.py --both --name="smith j" --date=01012018 --descending')
        self.parser.add_argument("-b", "--both", action="store_true")
        self.parser.add_argument("--grantor", action="store_true")
        self.parser.add_argument("--grantee", action="store_true")
        self.parser.add_argument("-n", "--name", required=True, help="Name of the party to search; Last name first")
        self.parser.add_argument("-d", "--date", default='', help="Will search from date forward; Format: MMDDYYYY")
        self.parser.add_argument("-o", "--output", default="index.html", help="path to html output; default is ./index.html")
        self.parser.add_argument('--descending', action="store_true", help="Default is ascending (earlier to later); This flag sorts (later to earlier)")
        return self.parser.parse_args()
        


LeaCountyIndexer()