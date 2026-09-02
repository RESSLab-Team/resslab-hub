"""Dump the CIS/2 (CIMsteel STEP) model of the AISC sculpture.

  python3 tools/cis2dump.py "<plans>/Model - CIS2/AISC Sculpture.stp" out.json

Prints every assembly with its members (section, length, global start and
end, inches), then the plates, the bolt groups (count, diameter, grade,
position) and the welds. The model frame is +x west, +y south, z up.
reference/sculpture.yaml was built from this output, see
reference/SCULPTURE.md. Rough parser, written for this one file.
"""
import re,sys,math,json
txt=open(sys.argv[1]).read().split('DATA;',1)[1]
ents=re.split(r';\s*\n(?=#)', txt)
d={}
for e in ents:
    m=re.match(r'\s*#(\d+)=(.*)', e, re.S)
    if m: d[int(m.group(1))]=re.sub(r'\s*\n\s*','',m.group(2))
def args(s):
    # split top-level args of NAME(...)
    i=s.index('('); body=s[i+1:-1]
    out=[];depth=0;cur=''
    for ch in body:
        if ch=='(':depth+=1
        if ch==')':depth-=1
        if ch==',' and depth==0: out.append(cur);cur=''
        else: cur+=ch
    out.append(cur); return [a.strip() for a in out]
def ref(s): return int(s[1:])
def num(s): return float(s)
def measure(r):
    s=d[r]; m=re.search(r'MEASURE\(([-\d.eE]+)\)',s); return float(m.group(1))
def point(r):
    s=d[r]; return tuple(float(x) for x in re.search(r'\(([-0-9.eE ,]+)\)\)',s).group(1).split(','))
def placement(r):
    s=d[r]
    if 'COORD_SYSTEM' in s[:40]:
        m=re.search(r'COORD_SYSTEM_CARTESIAN_3D\((#\d+)\)',s)
        if m: r=ref(m.group(1))
        else: r=ref(args(s)[4])
        s=d[r]
    a=args(s); o=point(ref(a[1])); z=point(ref(a[2])); x=point(ref(a[3]))
    y=(z[1]*x[2]-z[2]*x[1], z[2]*x[0]-z[0]*x[2], z[0]*x[1]-z[1]*x[0])
    return o,x,y,z
def compose(P,Q):
    # global = P applied to (Q applied to local)
    o1,x1,y1,z1=P; o2,x2,y2,z2=Q
    def T(v): return tuple(o1[i]+x1[i]*v[0]+y1[i]*v[1]+z1[i]*v[2] for i in range(3))
    def R(v): return tuple(x1[i]*v[0]+y1[i]*v[1]+z1[i]*v[2] for i in range(3))
    return T(o2),R(x2),R(y2),R(z2)
# sections
sec={}
for k,v in d.items():
    if v.startswith('SECTION_PROFILE'):
        a=args(v); sec[k]=a[1].strip("'")
# parts
parts={}
for k,v in d.items():
    if v.startswith('PART('):
        a=args(v); parts[k]=dict(name=a[1].strip("'"),kind='other',mat='')
    if v.startswith('(PART('):
        m=re.search(r'STRUCTURAL_FRAME_ITEM\((\d+),\'([^\']*)\'',v); name=m.group(2)
        mp=re.search(r'PART_PRISMATIC_SIMPLE\((#\d+),(#\d+)',v)
        ms=re.search(r'PART_SHEET_BOUNDED_SIMPLE\((#\d+)',v)
        mc=re.search(r'PART_SHEET_PROFILED\((#\d+)',v)
        mm=re.search(r'PRODUCT_WITH_MATERIAL\((#\d+|\$)',v)
        mat=d[ref(mm.group(1))].split("'")[1] if mm and mm.group(1)!='$' else ''
        if mp:
            parts[k]=dict(name=name,kind='prism',section=sec[ref(mp.group(1))],length=measure(ref(mp.group(2))),mat=mat)
        elif ms:
            th=measure(ref(ms.group(1)))
            outline=None
            if mc:
                c=d[ref(mc.group(1))]
                pts=re.findall(r'#\d+',c)
                # contour -> polyline points
                try:
                    poly=[p for p in re.findall(r'#\d+',d[ref(pts[0])])]
                except Exception: poly=[]
                outline=[]
                for p in re.findall(r'#\d+',c):
                    s=d[ref(p)]
                    if s.startswith('POLYLINE'):
                        outline=[point(ref(q)) for q in re.findall(r'#\d+',s)]
            parts[k]=dict(name=name,kind='plate',thick=th,mat=mat,outline=outline)
        else:
            parts[k]=dict(name=name,kind='other',mat=mat)
# ---- plates: designation + outline bbox
print("\n### PLATES")
for k,v in d.items():
    if v.startswith('(PART(') and 'PART_SHEET' in v:
        m=re.search(r"STRUCTURAL_FRAME_ITEM\((\d+),'([^']*)',('([^']*)'|\$)",v)
        mt=re.search(r'PART_SHEET\((#\d+)\)',v)
        th=measure(ref(mt.group(1))) if mt else 0
        parts[k]['desig']=(m.group(4) or parts[k]['name']) if m else '?'; parts[k]['thick']=th
# assemblies
asm={}
for k,v in d.items():
    if v.startswith('LOCATED_ASSEMBLY_MARKED'):
        a=args(v); asm[k]=dict(mark=a[1].strip("'"),type=a[2].strip("'"),pl=placement(ref(a[3])),parts=[])
for k,v in d.items():
    if v.startswith('LOCATED_PART_MARKED'):
        a=args(v); pk=ref(a[4]); ak=ref(a[5]); pl=placement(ref(a[3]))
        p=dict(parts[pk]); p['pl']=pl; p['qty']=int(a[9]); p['main']=a[10]=='.T.'
        asm[ak]['parts'].append(p)
json.dump({str(k):dict(mark=v['mark'],type=v['type'],o=v['pl'][0],x=v['pl'][1],y=v['pl'][2],z=v['pl'][3],parts=[dict(p, pl=None, g=compose(v['pl'],p['pl'])) for p in v['parts']]) for k,v in asm.items()}, open(sys.argv[2],'w'), indent=1)
def f(v): return '(%s)'%','.join('%.1f'%c for c in v)
for k in sorted(asm):
    a=asm[k]; o,x,y,z=a['pl']
    print('== %s [%s] origin %s x%s z%s'%(a['mark'],a['type'],f(o),f(x),f(z)))
    for p in a['parts']:
        g=compose(a['pl'],p['pl'])
        if p['kind']=='prism':
            end=tuple(g[0][i]+g[1][i]*p['length'] for i in range(3))
            print('   %-6s %-16s L=%6.1f  %s -> %s  %s%s'%(p['name'],p['section'],p['length'],f(g[0]),f(end),'MAIN ' if p['main'] else '', 'x%d'%p['qty'] if p['qty']>1 else ''))
        elif p['kind']=='plate':
            print('   %-6s PL t=%.3f at %s  z%s n=%d %s'%(p['name'],p['thick'],f(g[0]),f(g[3]),len(p['outline'] or []),'x%d'%p['qty'] if p['qty']>1 else ''))
        else:
            print('   %-6s other at %s'%(p['name'],f(g[0])))

# ---- bolts
print("\n### BOLT GROUPS (assembly, count, dia, global centre)")
asm_by_id={k:v for k,v in asm.items()}
tot=0
for k in sorted(d):
    v=d[k]
    if v.startswith('LOCATED_JOINT_SYSTEM'):
        a=args(v); js=d[ref(a[4])]; ak=ref(a[5]); pl=placement(ref(a[3]))
        if js.startswith('JOINT_SYSTEM_MECHANICAL'):
            ja=args(js); pts=re.findall(r'#\d+',ja[4]); n=len(pts)
            fm=d[ref(ja[5])]; bolt=d[ref(re.findall(r'#\d+',args(fm)[5])[0])]
            ba=args(bolt); dia=measure(ref(ba[5])); ln=measure(ref(ba[6])); grade=ba[4].strip("'"); kind=ba[1].strip("'")
            g=compose(asm[ak]['pl'],pl)
            tot+=n
            print('  %-5s n=%2d  %s dia=%.2f L=%.2f %-10s at %s  desc=%s'%(asm[ak]['mark'],n,grade,dia,ln,kind,f(g[0]),a[2].strip("'")))
print('  total bolts',tot)
print("\n### WELDS per assembly")
import collections
w=collections.defaultdict(list)
for k in sorted(d):
    v=d[k]
    if v.startswith('LOCATED_JOINT_SYSTEM'):
        a=args(v); js=d[ref(a[4])]; ak=ref(a[5])
        if js.startswith('JOINT_SYSTEM_WELDED'):
            w[asm[ak]['mark']].append(args(js)[2].strip("'").strip())
for m_ in w: print('  %-5s %d welds: %s'%(m_,len(w[m_]),'; '.join(w[m_])))
print("\n### PLATE LIST")
for k in sorted(asm):
    for p in asm[k]['parts']:
        if p.get('desig'):
            g=compose(asm[k]['pl'],p['pl'])
            print('  %-5s %-6s %-14s t=%.3f at %s normal%s %s'%(asm[k]['mark'],p['name'],p['desig'],p['thick'],f(g[0]),f(g[3]),'x%d'%p['qty'] if p['qty']>1 else ''))
