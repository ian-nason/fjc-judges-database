import importlib.util,pathlib,tempfile,csv,unittest,duckdb,subprocess,os,sys
REPO=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('builder',REPO/'build_database.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)

class PrecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name);self.old_raw=b.RAW;b.RAW=self.root
        self.c=duckdb.connect(config={'memory_limit':'64MB','threads':'1','max_temp_directory_size':'0B'})
    def tearDown(self):self.c.close();b.RAW=self.old_raw;self.tmp.cleanup()
    def write(self,table,header,rows):
        with (self.root/b.FILES[table]).open('w',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(rows)
    def test_year_only_service_keeps_precision_and_legacy_date(self):
        self.write('federal_judicial_service',['nid','Service as Chief Judge Begin'],[['1','1982'],['2','1982-07-01'],['3','']]);b.load(self.c,'federal_judicial_service')
        rows=self.c.execute('SELECT nid,chief_judge_begin,chief_judge_begin_year FROM federal_judicial_service ORDER BY nid').fetchall()
        self.assertEqual(rows[0],(1,None,1982));self.assertEqual(str(rows[1][1]),'1982-07-01');self.assertEqual(rows[1][2],1982);self.assertEqual(rows[2],(3,None,None))
    def test_approximate_birth_and_degree_years_preserve_source(self):
        self.write('judges',['nid','Birth Year'],[['1','ca. 1793'],['2','1982']]);b.load(self.c,'judges')
        self.assertEqual(self.c.execute('SELECT birth_year,birth_year_raw FROM judges ORDER BY nid').fetchall(),[(None,'ca. 1793'),(1982,'1982')])
        self.write('education',['nid','Degree Year'],[['1','1949-1951']]);b.load(self.c,'education')
        self.assertEqual(self.c.execute('SELECT degree_year,degree_year_raw FROM education').fetchone(),(None,'1949-1951'))
    def test_unsupported_service_precision_stops(self):
        self.write('federal_judicial_service',['nid','Service as Chief Judge Begin'],[['1','ca. 1982']])
        with self.assertRaisesRegex(ValueError,'unsupported source date precision'):b.load(self.c,'federal_judicial_service')
    def test_nonchief_date_loss_stops(self):
        self.write('federal_judicial_service',['nid','Senior Status Date'],[['1','2026']])
        with self.assertRaisesRegex(ValueError,'unparseable source DATE'):b.load(self.c,'federal_judicial_service')
    def test_integer_loss_or_rounding_stops(self):
        for value in ['unknown','1982.5','999999999999999999999']:
            self.write('judges',['nid','Death Year'],[['1',value]])
            with self.assertRaisesRegex(ValueError,'unparseable source INTEGER'):b.load(self.c,'judges')
    def test_missing_sources_do_not_create_database(self):
        output=self.root/'missing.duckdb'
        result=subprocess.run([sys.executable,str(REPO/'build_database.py'),'--raw-dir',str(self.root),'--output',str(output),'--dictionary',str(self.root/'dictionary.md')],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertFalse(output.exists());self.assertIn('Missing raw sources',result.stderr)
    def test_refuse_existing_artifact(self):
        p=self.root/'existing.duckdb';p.write_bytes(b'keep')
        result=subprocess.run([sys.executable,str(REPO/'build_database.py'),'--output',str(p)],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertEqual(p.read_bytes(),b'keep');self.assertIn('Refusing to overwrite',result.stderr)
    def test_failed_refresh_preserves_cached_source(self):
        target=self.root/'raw';target.mkdir();old=target/'judges.csv';old.write_bytes(b'old valid source')
        (self.root/'bin').mkdir();fake=self.root/'bin/curl';fake.write_text('#!/bin/sh\nexit 22\n');fake.chmod(0o700)
        env=dict(os.environ,PATH=str(self.root/'bin')+':'+os.environ['PATH'])
        result=subprocess.run(['bash',str(REPO/'download_data.sh'),'--refresh','--output-dir',str(target)],env=env,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0);self.assertEqual(old.read_bytes(),b'old valid source')

if __name__=='__main__':unittest.main()
