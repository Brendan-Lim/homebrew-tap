#!/usr/bin/env python3
"""Check local Markdown links against Git's index; ignored local reports cannot mask broken public links."""
import argparse
from pathlib import Path
import posixpath
import re
import subprocess
import urllib.parse

ROOT=Path(__file__).resolve().parents[1]


def tracked_files(root):
    return set(subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0'))-{''}


def text_at(root,name):
    return subprocess.check_output(['git','-C',str(root),'show',':'+name]).decode('utf-8',errors='replace')


def without_fences(text):
    return re.sub(r'^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$',lambda m:'\n'*m.group().count('\n'),text,flags=re.M|re.S)


def anchors(text):
    result=set(re.findall(r'<a\s+[^>]*(?:id|name)=[\x22\x27]([^\x22\x27]+)',text,re.I));counts={}
    for heading in re.findall(r'^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$',without_fences(text),re.M):
        heading=re.sub(r'<[^>]+>','',heading)
        base=re.sub(r'[^\w\- ]','',heading.lower()).replace(' ','-')
        n=counts.get(base,0);counts[base]=n+1
        result.add(base+('-'+str(n) if n else ''))
    return result


def inline_links(text):
    result=[]
    for match in re.finditer(r'!?\[[^\]\n]*\]\(',text):
        start=match.end()
        if text[start:start+1]=='<':
            end=text.find('>',start+1)
            if end>=0:result.append((match.start(),text[start+1:end]))
            continue
        target=[];depth=0;i=start
        while i<len(text):
            char=text[i]
            if char=='\\' and i+1<len(text):target.append(text[i+1]);i+=2;continue
            if char=='(' :depth+=1
            elif char==')':
                if depth==0:break
                depth-=1
            elif char.isspace() and depth==0:break
            target.append(char);i+=1
        if target:result.append((match.start(),''.join(target)))
    return result


def check_repository(root):
    root=Path(root);files=tracked_files(root);findings=[];links=0;external=set();markdown=0
    cache={}
    for name in sorted(files):
        if not name.endswith('.md'):continue
        markdown+=1;text=without_fences(text_at(root,name))
        refs={key.lower():value.strip('<>') for key,value in re.findall(r'^\s*\[([^\]]+)\]:\s*(<[^>]+>|\S+)',text,re.M)}
        candidates=inline_links(text)
        for match in re.finditer(r'!?\[([^\]\n]+)\]\[([^\]\n]*)\]',text):
            key=(match.group(2) or match.group(1)).lower()
            if key in refs:candidates.append((match.start(),refs[key]))
            else: findings.append({'path':name,'line':text[:match.start()].count('\n')+1,'reason':'undefined reference link'})
        candidates += [(m.start(),m.group(1)) for m in re.finditer(r'<(?:img|a)\s+[^>]*(?:src|href)=[\x22\x27]([^\x22\x27]+)',text,re.I)]
        for offset,target in candidates:
            line=text[:offset].count('\n')+1;parsed=urllib.parse.urlsplit(target)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme=='file':findings.append({'path':name,'line':line,'reason':'filesystem URL is not public'})
                else: external.add(target)
                continue
            links+=1;path=urllib.parse.unquote(parsed.path)
            destination=posixpath.normpath(path.lstrip('/') if path.startswith('/') else posixpath.join(posixpath.dirname(name),path)) if path else name
            if destination not in files and not any(f.startswith(destination.rstrip('/')+'/') for f in files):
                findings.append({'path':name,'line':line,'reason':'local destination is not tracked/public'});continue
            if parsed.fragment and destination.endswith('.md') and destination in files:
                if destination not in cache:cache[destination]=anchors(text_at(root,destination))
                if urllib.parse.unquote(parsed.fragment).lower() not in cache[destination]:
                    findings.append({'path':name,'line':line,'reason':'Markdown heading anchor does not exist'})
    return {'markdownFiles':markdown,'localLinks':links,'externalURLsNotFetched':len(external),'findings':findings}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    try:result=check_repository(args.root)
    except (OSError,ValueError,subprocess.CalledProcessError):
        print('Public link check could not complete; inspect repository/index syntax.');return 2
    for finding in result['findings']:print(f"{finding['path']}:{finding['line']}: {finding['reason']}")
    print(f"Public Markdown: {result['markdownFiles']} files, {result['localLinks']} local links, {len(result['findings'])} findings; {result['externalURLsNotFetched']} external URLs need separate network review.")
    return 1 if result['findings'] else 0


if __name__=='__main__':raise SystemExit(main())
