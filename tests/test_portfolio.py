import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from portfolio import load_portfolio

class PortfolioTests(unittest.TestCase):
    def test_optional_and_invalid_catalogs(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'portfolio.json'
            self.assertEqual(load_portfolio(directory)['projects'],[])
            project=dict(id='demo',title='Demo',summary='Example',tracks=['backend'],steps=['Inspect a contract'])
            for patch in ({'tracks':['unknown']},{'repoUrl':'javascript:alert(1)'},{'repoUrl':'https://github.com.evil.test/x/y'},{'steps':[]},{'id':'../escape'}):
                path.write_text(json.dumps(dict(version=1,projects=[{**project,**patch}])))
                result=load_portfolio(directory)
                self.assertEqual(result['projects'],[]);self.assertIn('error',result)
            path.write_text(json.dumps(dict(version=1,projects=[project,project])))
            self.assertIn('error',load_portfolio(directory))
            path.write_text(json.dumps(dict(version=1,projects=[project])))
            self.assertEqual(load_portfolio(directory)['projects'][0]['title'],'Demo')
            path.write_text('{invalid')
            self.assertIn('error',load_portfolio(directory))
if __name__=='__main__':unittest.main()
