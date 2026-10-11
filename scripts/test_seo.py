import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('seo',Path(__file__).with_name('check-seo.py'));seo=importlib.util.module_from_spec(spec);spec.loader.exec_module(seo)
class Regression(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
        shutil.copytree(seo.ROOT/'src',self.r/'src');shutil.copytree(seo.ROOT/'_site',self.r/'_site')
        self.baseline=json.loads((seo.ROOT/'scripts/seo-baseline.json').read_text())
        self.article=self.r/'_site/articles/20260924-manitoba-mpnp-draw-280.html'
    def tearDown(self):self.tmp.cleanup()
    def errors(self):return seo.validate(self.r,self.baseline)[0]
    def edit(self,p,old,new):p.write_text(p.read_text().replace(old,new))
    def test_current_site(self):self.assertEqual(self.errors(),[])
    def test_wrong_canonical(self):
        self.edit(self.article,'rel="canonical"','rel="alternate"');self.assertTrue(any('Canonical mismatch' in e for e in self.errors()))
    def test_sitemap_omission(self):
        p=self.r/'_site/sitemap.xml';self.edit(p,'https://ellenlinrcic.ca/articles/20260924-manitoba-mpnp-draw-280','https://ellenlinrcic.ca/articles/missing');self.assertTrue(any('missing from sitemap' in e for e in self.errors()))
    def test_duplicate_sitemap(self):
        p=self.r/'_site/sitemap.xml';self.edit(p,'</urlset>','<url><loc>https://ellenlinrcic.ca/</loc></url></urlset>');self.assertIn('Duplicate sitemap URLs',self.errors())
    def test_broken_resource(self):
        self.article.write_text(self.article.read_text()+'<img src="/images/missing-new.jpg">');self.assertTrue(any('missing-new' in e for e in self.errors()))
    def test_relative_link(self):
        self.article.write_text(self.article.read_text()+'<a href="../consultation">x</a>');self.assertTrue(any('relative internal' in e for e in self.errors()))
    def test_noindex(self):
        self.article.write_text(self.article.read_text()+'<meta name="robots" content="noindex">');self.assertTrue(any('noindex' in e for e in self.errors()))
    def test_robots(self):
        (self.r/'_site/robots.txt').write_text('User-agent: *\nDisallow: /articles/\n');self.assertTrue(any('robots blocked' in e for e in self.errors()))
    def test_missing_404(self):
        (self.r/'_site/404.html').unlink();self.assertIn('Missing top-level 404.html',self.errors())
    def test_old_article_edit(self):
        p=next((self.r/'src/articles').glob('*.html'));p.write_text(p.read_text()+'changed');self.assertTrue(any('Protected file changed' in e for e in self.errors()))
    def test_duplicate_source_route(self):
        p=self.r/'src/articles/new.md';p.write_text((self.r/'src/articles/20260924-manitoba-mpnp-draw-280.md').read_text());self.assertTrue(any('Duplicate source' in e for e in self.errors()))
    def test_repeated_path(self):
        self.article.write_text(self.article.read_text()+'<a href="/articles/articles/foo">x</a>');self.assertTrue(any('Repeated articles' in e for e in self.errors()))
    def test_template_leak(self):
        self.article.write_text(self.article.read_text()+'{{ title }}');self.assertTrue(any('Unrendered' in e for e in self.errors()))
    def test_http_no_follow(self):
        self.assertIsNone(seo.NoRedirect().redirect_request(None,None,308,None,None,None))
    def test_live_status_contract(self):
        from unittest.mock import patch
        url=seo.ORIGIN+'/articles/example'
        def response(u):
            if u.endswith('sitemap.xml'):return 200,{},'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+url+'</loc></url></urlset>'
            if u.endswith('robots.txt'):return 200,{},'User-agent: *\nAllow: /'
            if u==url:return 200,{},'<link rel="canonical" href="'+url+'">'
            if u==url+'.html':return 308,{'Location':url},''
            return 404,{},''
        with patch.object(seo,'get',side_effect=response):self.assertEqual(seo.live(['/articles/example'],[url]),[])
        def broken(u):
            c,h,b=response(u)
            return (200,h,b) if c==404 else (301,h,b) if c==308 else (c,h,b)
        with patch.object(seo,'get',side_effect=broken):
            errors=seo.live(['/articles/example'],[url]);self.assertTrue(any('404' in e for e in errors));self.assertTrue(any('308' in e for e in errors))

    def test_real_validator_exit_codes(self):
        import subprocess
        self.assertEqual(self.errors(),[])
        (self.r/'scripts').mkdir()
        shutil.copy2(seo.ROOT/'scripts/check-seo.py',self.r/'scripts/check-seo.py')
        (self.r/'scripts/seo-baseline.json').write_text(json.dumps(self.baseline))
        command=['python3','scripts/check-seo.py','--skip-build']
        result=subprocess.run(command,cwd=self.r,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('6 documented exceptions',result.stdout)
        self.assertIn('DISPLAY CHECK: NOT RUN',result.stdout)
        self.edit(self.article,'name="description"','name="removed-description"')
        result=subprocess.run(command,cwd=self.r,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Missing/empty or multiple meta description',result.stdout)
        self.assertIn('6 documented exceptions',result.stdout)
    def test_english_filename(self):
        p=self.r/'src/articles/中文.md'
        p.write_text((self.r/'src/articles/20260924-manitoba-mpnp-draw-280.md').read_text())
        self.assertTrue(any('Invalid English article filename' in e for e in self.errors()))
    def test_duplicate_canonical(self):
        self.article.write_text(self.article.read_text()+'<link rel="canonical" href="https://ellenlinrcic.ca/articles/20260924-manitoba-mpnp-draw-280">')
        self.assertTrue(any('Canonical mismatch' in e for e in self.errors()))

class Metadata(unittest.TestCase):
    def scan(self,title='Example',description='Example description'):
        return seo.Scan('<title>'+title+'</title><meta name="description" content="'+description+'">')
    def test_missing_title_and_description(self):
        errors,_=seo.metadata_issues([('/a',seo.Scan('<h1>Body</h1>'))])
        self.assertEqual(len(errors),2)
    def test_empty_metadata(self):
        errors,_=seo.metadata_issues([('/a',self.scan('   ','  '))]);self.assertEqual(len(errors),2)
    def test_multiple_metadata(self):
        s=seo.Scan('<title>A</title><title>B</title><meta name="description" content="A"><meta name="description" content="B">')
        self.assertEqual(len(seo.metadata_issues([('/a',s)])[0]),2)
    def test_similarity_is_advisory(self):
        errors,warnings=seo.metadata_issues([('/a',self.scan()),('/b',self.scan()),('/c',self.scan('Other','Example description!'))])
        self.assertEqual(errors,[]);self.assertTrue(any('duplicate title' in w for w in warnings));self.assertTrue(any('similar descriptions' in w for w in warnings))
    def test_distinct_metadata(self):
        self.assertEqual(seo.metadata_issues([('/a',self.scan()),('/b',self.scan('Unique','A wholly different topic with its own summary'))]),([],[]))
    def test_title_entities_and_nested_text(self):
        s=seo.Scan('<title>A &amp; B</title><meta name="description" content="A &amp; B">')
        self.assertEqual(s.titles,['A & B']);self.assertEqual(s.descriptions,['A & B'])

class BuildGate(unittest.TestCase):
    def test_build_success_and_failures_without_recursion(self):
        import subprocess
        # Exercise actual npm wiring in an isolated project, with no website edits.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir()
            package=json.loads((seo.ROOT/'package.json').read_text())
            package['scripts']['build:raw']='node -e "process.exit(0)"'
            (root/'package.json').write_text(json.dumps(package))
            script=root/'scripts/check-seo.py'
            script.write_text('import sys\nassert "--skip-build" in sys.argv\nprint("VALIDATOR_CALLED")\n')
            result=subprocess.run(['npm','run','build'],cwd=root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0);self.assertEqual(result.stdout.count('VALIDATOR_CALLED'),1)
            script.write_text('import sys\nprint("CRITICAL_FAILURE")\nsys.exit(1)\n')
            result=subprocess.run(['npm','run','build'],cwd=root,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertIn('CRITICAL_FAILURE',result.stdout)
            package['scripts']['build:raw']='node -e "process.exit(7)"'
            (root/'package.json').write_text(json.dumps(package))
            result=subprocess.run(['npm','run','build'],cwd=root,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0);self.assertNotIn('CRITICAL_FAILURE',result.stdout)
