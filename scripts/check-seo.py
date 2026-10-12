#!/usr/bin/env python3
"""Offline output validation; --live adds explicit production HTTP verification."""
import argparse, hashlib, importlib.util, json, re, subprocess, sys
from difflib import SequenceMatcher
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, unquote
import urllib.request, urllib.error, urllib.robotparser
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
province_spec=importlib.util.spec_from_file_location('province_insights',Path(__file__).with_name('province_insights.py'))
province_insights=importlib.util.module_from_spec(province_spec);province_spec.loader.exec_module(province_insights)
ORIGIN='https://ellenlinrcic.ca'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def route(p):
    s='/'+p.as_posix()
    return s[:-10] if s.endswith('index.html') else s[:-5] if s.endswith('.html') else s
class Scan(HTMLParser):
    def __init__(self,text):
        super().__init__(); self.canonical=[]; self.refs=[]; self.robots=[]; self.h1=0; self.titles=[]; self.descriptions=[]; self.in_title=False; self.feed(text)
    def handle_starttag(self,t,attrs):
        a=dict(attrs)
        if t=='title': self.titles.append(''); self.in_title=True
        if t=='meta' and a.get('name','').lower()=='description': self.descriptions.append(a.get('content',''))
        if t=='link' and 'canonical' in a.get('rel','').lower().split(): self.canonical.append(a.get('href',''))
        if t=='meta' and a.get('name','').lower() in ('robots','googlebot'): self.robots.append(a.get('content','').lower())
        if t=='h1': self.h1+=1
        for k in ('href','src','action','poster'):
            if k in a: self.refs.append((k,a[k]))
        if 'srcset' in a:
            self.refs.extend(('srcset',x.strip().split()[0]) for x in a['srcset'].split(',') if x.strip())
    def handle_data(self,data):
        if self.in_title: self.titles[-1]+=data
    def handle_endtag(self,t):
        if t=='title': self.in_title=False

def metadata_issues(records):
    """Missing/ambiguous metadata is fatal; editorial similarity needs review."""
    errors=[]; warnings=[]; titles={}; descriptions=[]
    norm=lambda value: ' '.join(value.split()).casefold()
    for route,s in records:
        for label,values in (('SEO title',s.titles),('meta description',s.descriptions)):
            if len(values)!=1 or not norm(values[0]):
                errors.append('Missing/empty or multiple '+label+': '+route)
        if len(s.titles)==1 and norm(s.titles[0]):
            title=norm(s.titles[0])
            if title in titles: warnings.append('SEO review: duplicate title: '+titles[title]+' and '+route)
            titles[title]=route
        if len(s.descriptions)==1 and norm(s.descriptions[0]):
            description=norm(s.descriptions[0])
            for other,previous in descriptions:
                if description==previous or SequenceMatcher(None,description,previous,autojunk=False).ratio()>=0.92:
                    warnings.append('SEO review: duplicate/highly similar descriptions: '+other+' and '+route)
            descriptions.append((route,description))
    return errors,warnings

def validate(root,baseline):
    errors=[];warnings=[]
    def check(ok,msg):
        if not ok: errors.append(msg)
    for name,h in baseline['protected'].items():
        p=root/name;check(p.is_file() and digest(p)==h,'Protected file changed/deleted: '+name)
    out=root/'_site'; pages={route(p.relative_to(out)):p for p in out.rglob('*.html')}
    check(len(pages)==len(list(out.rglob('*.html'))),'Duplicate output routes')
    expected=[]
    for p in (root/'src/articles').rglob('*'):
        if p.suffix not in ('.md','.njk','.html'):continue
        check(bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p.stem)), 'Invalid English article filename: '+p.name)
        if p.suffix=='.html': r=route(p.relative_to(root/'src'))
        else:
            text=p.read_text(); fm=text.split('---',2)
            check(len(fm)==3,'Missing front matter: '+p.name)
            data=fm[1] if len(fm)==3 else ''
            m=re.search(r'^permalink:\s*[\"\']?([^\"\'\n]+)',data,re.M)
            r=route(Path(m[1].strip().lstrip('/'))) if m else ''
            for field in (('layout','title','date','category','description','tags') if p.suffix=='.md' else ()):
                check(bool(re.search(r'^'+field+r':\s*\S',data,re.M)),'Missing '+field+': '+p.name)
            check(bool(re.fullmatch(r'/articles/[a-z0-9-]+',r)),'Invalid article permalink: '+p.name)
        expected.append(r); check(r in pages,'Article not emitted as HTML: '+r)
    check(len(expected)==len(set(expected)),'Duplicate source article routes (including legacy HTML)')
    check(set(r for r in pages if r.startswith('/articles/'))==set(expected),'Unexpected/missing article output')
    try:
        urls=[x.text for x in ET.parse(out/'sitemap.xml').iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    except Exception as e: errors.append('Invalid sitemap: '+str(e));urls=[]
    check(len(urls)==len(set(urls)),'Duplicate sitemap URLs')
    for u in urls:
        check(u.startswith(ORIGIN+'/') and urlsplit(u).path in pages and u==ORIGIN+urlsplit(u).path,'Invalid sitemap target: '+str(u))
        check(not u.endswith('.html') and '/articles/articles/' not in u,'Noncanonical sitemap URL: '+u)
    robots=urllib.robotparser.RobotFileParser();robots.parse((out/'robots.txt').read_text().splitlines())
    check('Sitemap: '+ORIGIN+'/sitemap.xml' in (out/'robots.txt').read_text(),'Missing robots sitemap declaration')
    headers=(out/'_headers').read_text() if (out/'_headers').exists() else ''
    check(not re.search(r'X-Robots-Tag\s*:.*(?:noindex|none)',headers,re.I),'Blocking X-Robots-Tag in _headers (review scope)')
    metadata=[]
    inbound=set(); known=baseline['known_refs']; seen=set()
    for r,p in pages.items():
        text=p.read_text();s=Scan(text)
        check('/articles/articles/' not in text,'Repeated articles path: '+r)
        check(not re.search(r'\{\{|\{%|<%=',text),'Unrendered template syntax: '+r)
        if r in expected or ORIGIN+r in urls:
            check(s.canonical==[ORIGIN+r],'Canonical mismatch: '+r)
        if r in expected:
            metadata.append((r,s))
            check(ORIGIN+r in urls,'Article missing from sitemap: '+r)
            check(s.h1>0 and len(re.sub('<[^>]*>','',text))>200,'Missing static article content: '+r)
            check(not any(re.search(r'\b(noindex|none)\b',x) for x in s.robots),'Article noindex: '+r)
            check(robots.can_fetch('Googlebot',ORIGIN+r) and robots.can_fetch('*',ORIGIN+r),'Article robots blocked: '+r)
        for kind,v in s.refs:
            u=urlsplit(urljoin(ORIGIN+r,v))
            if u.netloc!=urlsplit(ORIGIN).netloc or u.scheme not in ('http','https'):continue
            path=unquote(u.path);key=r+'|'+kind+'|'+v
            target=out/path.lstrip('/');resolved=path in pages or target.is_file() or Path(str(target)+'.html').is_file() or (target/'index.html').is_file()
            relative=not v.startswith(('/','#')) and not urlsplit(v).scheme
            if not resolved or relative:
                if key in known: warnings.append('Existing exception: '+key);seen.add(key)
                else: errors.append('Broken/relative internal reference: '+key)
            if kind=='href' and not r.startswith('/articles/'):
                inbound.add(path.removesuffix('.html'))
    metadata_errors,metadata_warnings=metadata_issues(metadata)
    errors.extend(metadata_errors); warnings.extend(metadata_warnings)
    for r in expected:
        if r not in inbound and r in baseline.get('known_orphans',[]): warnings.append('Existing static discovery exception: '+r)
        else: check(r in inbound,'Article lacks static homepage/category link: '+r)
    check((out/'404.html').is_file(),'Missing top-level 404.html')
    if (out/'404.html').exists():check(any('noindex' in x for x in Scan((out/'404.html').read_text()).robots),'404 must be noindex')
    check(ORIGIN+'/404' not in urls,'404 in sitemap')
    errors.extend(province_insights.validate(root,expected))
    warnings.extend(province_insights.review_warnings(root))
    return errors,warnings,expected,urls
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None
def get(url):
    try:
        with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; EllenLinSEOCheck/1.0)'}),timeout=25) as r:return r.status,r.headers,r.read().decode('utf-8')
    except urllib.error.HTTPError as e:return e.code,e.headers,e.read().decode('utf-8')
def live(articles,urls):
    errors=[]
    def check(ok,msg):
        if not ok:errors.append(msg)
    for u in urls:
        c,h,b=get(u);check(c==200,'Live expected 200: '+u+' got '+str(c))
        check(Scan(b).canonical==[u],'Live canonical mismatch: '+u)
        if urlsplit(u).path in articles:
            check(not any(re.search(r'\b(noindex|none)\b',x) for x in Scan(b).robots) and not re.search(r'noindex|none',h.get('X-Robots-Tag',''),re.I),'Live noindex: '+u)
        old=u+'index.html' if u.endswith('/') else u+'.html'
        c,h,b=get(old);check(c==308 and urljoin(old,h.get('Location',''))==u,'Live expected 308 to canonical: '+old)
    for p in ('/seo-check-nonexistent-7b41','/articles/seo-check-nonexistent-7b41','/articles/seo-check-nonexistent-7b41.html','/articles/articles/20260924-manitoba-mpnp-draw-280'):
        c,h,b=get(ORIGIN+p);check(c==404,'Live expected 404: '+p+' got '+str(c))
    c,h,b=get(ORIGIN+'/sitemap.xml')
    actual=[x.text for x in ET.fromstring(b).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    check(c==200 and sorted(actual)==sorted(urls),'Live sitemap differs from checked build')
    c,h,b=get(ORIGIN+'/robots.txt');rp=urllib.robotparser.RobotFileParser();rp.parse(b.splitlines())
    check(c==200 and all(rp.can_fetch('Googlebot',ORIGIN+r) for r in articles),'Live robots blocks articles')
    return errors
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--skip-build',action='store_true',help='Validate an already generated _site without rebuilding');args=parser.parse_args()
    if not args.skip_build: subprocess.run(['npm','run','build:raw'],cwd=ROOT,check=True)
    baseline=json.loads((ROOT/'scripts/seo-baseline.json').read_text())
    errors,warnings,articles,urls=validate(ROOT,baseline)
    for x in warnings:print('WARNING:',x)
    for x in errors:print('FAIL:',x)
    print(f'BUILD CHECK: {len(articles)} articles, {len(urls)} sitemap URLs, {len(errors)} errors, {sum(x.startswith("Existing ") for x in warnings)} documented exceptions, {sum(x.startswith("SEO review:") for x in warnings)} SEO review warnings. No HTTP status verified by build checks.')
    print('DISPLAY CHECK: NOT RUN by this static checker; desktop/mobile browser review is required. Google indexing: NOT VERIFIED.')
    if not errors and args.live:
        try:errors=live(articles,urls)
        except Exception as e:errors=['Live verification incomplete: '+str(e)]
        for x in errors:print('FAIL:',x)
        print('LIVE HTTP CHECK:', 'FAIL' if errors else 'PASS (200 / 404 / 308)')
    sys.exit(bool(errors))
