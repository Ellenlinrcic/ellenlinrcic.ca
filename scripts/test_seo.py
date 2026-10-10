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
