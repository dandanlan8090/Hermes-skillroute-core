#!/usr/bin/env python3
"""PPTX 几何校验：超界 + 两两重叠检测。
用法: python3 geom_check.py <file.pptx>
输出每页超界形状与重叠对（已跳过装饰/标题/有意叠放）。
"""
import sys, zipfile
from xml.etree import ElementTree as ET

P  = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A  = 'http://schemas.openxmlformats.org/drawingml/2006/main'
W, H = 12192000, 6858000        # 16:9 画布 EMU 上限
TOL  = 50000                     # 重叠容差 EMU
SKIP = ('Deco', 'Part', 'TB', 'SB', 'Row', 'Val', 'Arw')  # 装饰/标题/有意叠放前缀

def shapes(slide_xml):
    root = ET.fromstring(slide_xml)
    out = []
    for sp in root.iter(f'{{{P}}}sp'):
        xf = sp.find(f'.//{{{A}}}xfrm')
        if xf is None: continue
        off = xf.find(f'{{{A}}}off'); ext = xf.find(f'{{{A}}}ext')
        if off is None or ext is None: continue
        x, y, cx, cy = (int(off.get('x')), int(off.get('y')),
                          int(ext.get('cx')), int(ext.get('cy')))
        nm = '?'
        nv = sp.find(f'{{{P}}}nvSpPr')
        if nv is not None:
            c = nv.find(f'{{{P}}}cNvPr')
            if c is not None: nm = c.get('name', '?')
        if nm.startswith(SKIP): continue
        out.append((nm, x, y, cx, cy))
    return out

def overlap(a, b):
    _, x1, y1, cx1, cy1 = a; _, x2, y2, cx2, cy2 = b
    ix = max(0, min(x1+cx1, x2+cx2) - max(x1, x2))
    iy = max(0, min(y1+cy1, y2+cy2) - max(y1, y2))
    return ix > TOL and iy > TOL

def main():
    if len(sys.argv) < 2:
        print('用法: geom_check.py <file.pptx>'); sys.exit(1)
    z = zipfile.ZipFile(sys.argv[1])
    slides = sorted([n for n in z.namelist()
                    if n.startswith('ppt/slides/slide') and n.endswith('.xml')],
                   key=lambda s: int(s.split('slide')[1].split('.')[0]))
    allok = True
    for fn in slides:
        s = int(fn.split('slide')[1].split('.')[0])
        gs = shapes(z.read(fn))
        over = [g[0] for g in gs if g[1]+g[3] > W or g[2]+g[4] > H]
        issues = []
        for i in range(len(gs)):
            for j in range(i+1, len(gs)):
                if overlap(gs[i], gs[j]):
                    issues.append(f'{gs[i][0]}<->{gs[j][0]}')
        if over or issues:
            allok = False
            print(f'Slide {s}: 超界={over} 重叠={issues}')
    print('全局:', '✓ 全部无超界无重叠' if allok else '✗ 仍有问题(见上)')

if __name__ == '__main__':
    main()
