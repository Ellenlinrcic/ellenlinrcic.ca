import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('seo',Path(__file__).with_name('check-seo.py'));seo=importlib.util.module_from_spec(spec);spec.loader.exec_module(seo)
class Regression(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
        shutil.copytree(seo.ROOT/'src',self.r/'src');shutil.copytree(seo.ROOT/'_site',self.r/'_site')
        self.baseline=json.loads((seo.ROOT/'scripts/seo-baseline.json').read_text())
        (self.r/'scripts').mkdir()
        for name in ('province_insights.py','province-insights.json'):
            shutil.copy2(seo.ROOT/'scripts'/name,self.r/'scripts'/name)
        self.article=self.r/'_site/articles/20260924-manitoba-mpnp-draw-280.html'
    def tearDown(self):self.tmp.cleanup()
    def errors(self):return seo.validate(self.r,self.baseline)[0]
    def edit(self,p,old,new):p.write_text(p.read_text().replace(old,new))
    def test_current_site(self):self.assertEqual(self.errors(),[])
    def test_wrong_canonical(self):
        self.edit(self.article,'rel="canonical"','rel="alternate"');self.assertTrue(any('Canonical mismatch' in e for e in self.errors()))
    def test_non_article_canonical_contract(self):
        page=self.r/'_site/permanent-residence.html'
        original=page.read_text()
        canonical='https://ellenlinrcic.ca/permanent-residence'
        tag='<link rel="canonical" href="'+canonical+'">'
        for target in (canonical+'.html',seo.ORIGIN+'/consultation','http://ellenlinrcic.ca/permanent-residence',canonical+'?old=1',canonical+'#section'):
            with self.subTest(target=target):
                page.write_text(original.replace('href="'+canonical+'"','href="'+target+'"'))
                self.assertIn('Canonical mismatch: /permanent-residence',self.errors())
        for label,text in (('missing',original.replace('rel="canonical"','rel="alternate"')),('duplicate',original.replace('</head>',tag+'</head>'))):
            with self.subTest(case=label):
                page.write_text(text)
                self.assertIn('Canonical mismatch: /permanent-residence',self.errors())
        page.write_text(original)
        self.assertEqual(self.errors(),[])
    def test_homepage_canonical_contract(self):
        page=self.r/'_site/index.html';original=page.read_text()
        self.assertEqual(seo.Scan(original).canonical,[seo.ORIGIN+'/'])
        for target in (seo.ORIGIN,seo.ORIGIN+'/index.html'):
            with self.subTest(target=target):
                page.write_text(original.replace('href="'+seo.ORIGIN+'/"','href="'+target+'"'))
                self.assertIn('Canonical mismatch: /',self.errors())
    def test_sitemap_scope_excludes_noncanonical_alias(self):
        # /updates intentionally declares the homepage fragment and is outside this phase.
        self.assertEqual(seo.Scan((self.r/'_site/updates.html').read_text()).canonical,[seo.ORIGIN+'/#updates'])
        self.assertEqual(self.errors(),[])
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
        (self.r/'scripts').mkdir(exist_ok=True)
        shutil.copy2(seo.ROOT/'scripts/check-seo.py',self.r/'scripts/check-seo.py')
        (self.r/'scripts/seo-baseline.json').write_text(json.dumps(self.baseline))
        command=['python3','scripts/check-seo.py','--skip-build']
        result=subprocess.run(command,cwd=self.r,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assert_documented_exceptions(result.stdout)
        self.assertIn('DISPLAY CHECK: NOT RUN',result.stdout)
        self.edit(self.article,'name="description"','name="removed-description"')
        result=subprocess.run(command,cwd=self.r,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Missing/empty or multiple meta description',result.stdout)
        self.assert_documented_exceptions(result.stdout)
    def assert_documented_exceptions(self,output):
        expected=[
            'WARNING: Existing exception: /|href|/visitor-visas.html',
            'WARNING: Existing exception: /|href|/visitor-visas.html',
            'WARNING: Existing exception: /image-test|src|/images/%20work-permit-pr-banner.jpg',
            'WARNING: Existing exception: /image-test|src|/images/%20work-permit-pr-banner.jpg',
            'WARNING: Existing static discovery exception: /articles/pgwp-student-hunger-strike-2026',
        ]
        self.assertCountEqual([line for line in output.splitlines() if line.startswith('WARNING: Existing ')],expected)
        self.assertIn(str(len(expected))+' documented exceptions',output)
    def test_english_filename(self):
        p=self.r/'src/articles/中文.md'
        p.write_text((self.r/'src/articles/20260924-manitoba-mpnp-draw-280.md').read_text())
        self.assertTrue(any('Invalid English article filename' in e for e in self.errors()))
    def test_duplicate_canonical(self):
        self.article.write_text(self.article.read_text()+'<link rel="canonical" href="https://ellenlinrcic.ca/articles/20260924-manitoba-mpnp-draw-280">')
        self.assertTrue(any('Canonical mismatch' in e for e in self.errors()))

class LiveCanonical(unittest.TestCase):
    def test_all_sitemap_pages_require_unique_self_canonical(self):
        from unittest.mock import patch
        urls=[seo.ORIGIN+'/',seo.ORIGIN+'/permanent-residence']
        def response(u):
            if u.endswith('/sitemap.xml'):
                return 200,{},'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+url+'</loc></url>' for url in urls)+'</urlset>'
            if u.endswith('/robots.txt'):return 200,{},'User-agent: *\nAllow: /'
            if u in urls:return 200,{},'<link rel="canonical" href="'+u+'">'
            if u==seo.ORIGIN+'/index.html':return 308,{'Location':urls[0]},''
            if u==urls[1]+'.html':return 308,{'Location':urls[1]},''
            return 404,{},''
        with patch.object(seo,'get',side_effect=response):self.assertEqual(seo.live([],urls),[])
        for url in urls:
            for body in ('<title>Missing canonical</title>','<link rel="canonical" href="'+url+'.html">',('<link rel="canonical" href="'+url+'">')*2):
                with self.subTest(url=url,body=body):
                    def broken(u):return (200,{},body) if u==url else response(u)
                    with patch.object(seo,'get',side_effect=broken):
                        self.assertIn('Live canonical mismatch: '+url,seo.live([],urls))

class ProvinceInsights(unittest.TestCase):
    setUp=Regression.setUp
    tearDown=Regression.tearDown
    errors=Regression.errors
    edit=Regression.edit
    def test_historical_pending_review_is_nonblocking(self):
        self.assertEqual(self.errors(),[])
        warnings=seo.province_insights.review_warnings(self.r)
        self.assertEqual(len(warnings),1)
        self.assertIn('nonblocking',warnings[0])
    def test_explicit_nonprovincial_new_article_is_allowed(self):
        data=seo.province_insights.load(self.r)
        route='/articles/new-general-article'
        data['articles'][route]={'topics':[],'published':'2026-10-12'}
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        actual=[('/articles/'+p.stem) for p in (self.r/'src/articles').iterdir() if p.suffix in ('.md','.njk','.html')]
        self.assertEqual(seo.province_insights.validate(self.r,actual+[route]),[])
    def test_multiple_province_memberships_require_each_directory(self):
        data=seo.province_insights.load(self.r)
        route='/articles/20261008-bc-pnp-targeted-draw'
        data['articles'][route]['topics'].append('alberta')
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        self.assertIn('Province Insights missing entry: alberta '+route,self.errors())
        self.assertNotIn('Province Insights missing entry: bc '+route,self.errors())
    def test_missing_provincial_entry_fails(self):
        page=self.r/'_site/bc-pnp-insights.html'
        self.edit(page,'/articles/20261008-bc-pnp-targeted-draw','/articles/20260929-bc-pnp-september-four-draws')
        self.assertIn('Province Insights missing entry: bc /articles/20261008-bc-pnp-targeted-draw',self.errors())
    def test_duplicate_entry_fails(self):
        page=self.r/'_site/bc-pnp-insights.html'
        self.edit(page,'</ul>','<li><a href="/articles/20261008-bc-pnp-targeted-draw">Duplicate</a></li></ul>')
        self.assertIn('Province Insights duplicate entry: bc /articles/20261008-bc-pnp-targeted-draw',self.errors())
    def test_publication_order_fails(self):
        data=seo.province_insights.load(self.r)
        data['articles']['/articles/20261008-bc-pnp-targeted-draw']['published']='2020-01-01'
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        self.assertIn('Province Insights not ordered by publication date: bc',self.errors())
    def test_new_unclassified_article_requires_confirmation(self):
        data=seo.province_insights.load(self.r)
        route='/articles/20261008-bc-pnp-targeted-draw'
        del data['articles'][route]
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        self.assertTrue(any('Province association unresolved: '+route in error for error in self.errors()))
    def test_unknown_topic_fails(self):
        data=seo.province_insights.load(self.r)
        data['articles']['/articles/20261008-bc-pnp-targeted-draw']['topics']=['unknown-province']
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        self.assertTrue(any('Unknown province association' in error for error in self.errors()))
    def test_sync_refuses_duplicates_without_source_edits(self):
        page=self.r/'src/bc-pnp-insights.html'
        page.write_text(page.read_text().replace('</ul>','<li><a href="/articles/20261008-bc-pnp-targeted-draw">Duplicate</a></li></ul>'))
        sources={p:p.read_bytes() for p in (self.r/'src').glob('*insights*')}
        with self.assertRaisesRegex(ValueError,'Duplicate/unconfirmed'):
            seo.province_insights.synchronize(self.r)
        self.assertTrue(all(p.read_bytes()==contents for p,contents in sources.items()))
    def test_sync_inserts_once_and_preserves_existing_cards(self):
        page=self.r/'src/bc-pnp-insights.html';original=page.read_text()
        import re
        item=re.search(r'<li>\s*<span class="title-zh">BC省提名10月8日.*?</li>',original,re.S)
        self.assertIsNotNone(item)
        page.write_text(original[:item.start()]+original[item.end():])
        data=seo.province_insights.load(self.r)
        data['articles']['/articles/20261008-bc-pnp-targeted-draw'].update(title='Approved title',title_en='Approved English title',description='Approved summary')
        (self.r/'scripts/province-insights.json').write_text(json.dumps(data))
        other_cards=re.findall(r'<li\b[^>]*>.*?</li>',page.read_text(),re.S)
        changed=seo.province_insights.synchronize(self.r)
        self.assertEqual(changed,['src/bc-pnp-insights.html'])
        after=page.read_text()
        self.assertEqual(after.count('href="/articles/20261008-bc-pnp-targeted-draw"'),1)
        for card in other_cards:self.assertIn(card,after)
        self.assertLess(after.index('href="/articles/20261008-bc-pnp-targeted-draw"'),after.index('href="/articles/20260929-bc-pnp-september-four-draws.html"'))
        self.assertEqual(seo.province_insights.synchronize(self.r),[])


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
