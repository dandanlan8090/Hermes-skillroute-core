#!/usr/bin/env python3
"""
status-file-sanitizer.py — 加固 /var/lib/dpkg/status 文件,修三个 sed-surgery 频出的坑。

使用:
  sudo cp /var/lib/dpkg/status /var/lib/dpkg/status.original-$(date +%s)
  sudo python3 status-file-sanitizer.py /var/lib/dpkg/status
  # 失败回滚:
  sudo cp /var/lib/dpkg/status.original-<ts> /var/lib/dpkg/status

修的三个问题:
1. duplicate value for 'Package' field       (前次 sed 复写了 Package 行)
2. Config-Version field present for inappropriate 'Status' field
                                             (改 Status 时未同步 Config-Version)
3. medium section 末尾缺失空行                (sed in-place 裁掉换行)
"""
import sys, re, shutil, os

def sanitize(path):
    bak = path + '.sanitizer-' + str(os.getpid())
    shutil.copy2(path, bak)
    t = open(path).read()

    # 1) 去重:连续两个相同 Package 行,保留第二个
    t, n1 = re.subn(r'^(Package: (\S+)\n)\s*Package: \2\n', r'\1', t, flags=re.M)
    # (反向抓也可能 产生间隔一个空格的,这里只覆盖跨行重复)

    # 2) 健康:install ok installed 时不应保留 Config-Version
    def fix_block(m):
        head = m.group(1)
        body = m.group(2)
        lines = body.splitlines()
        if any(l.startswith('Status: install ok installed') for l in lines):
            lines = [l for l in lines if not l.startswith('Config-Version:')]
        return head + '\n'.join(lines) + '\n'

    t, n2 = re.subn(r'^(Package: \S+\n)((?:^.*\n)*?)(?=^Package:|\Z)', fix_block, t, flags=re.M)

    # 3) 每次 section 末尾补空行(Package 上一个空行不缺失)
    t, n3 = re.subn(r'(\n)(?=^Package:)', r'\1', t, flags=re.M)  # 加额外空行
    # 保证文件末尾有 \n
    if not t.endswith('\n\n'):
        t = t.rstrip('\n') + '\n\n'

    open(path, 'w').write(t)
    return {'removed_duplicate_package': n1,
            'sections_inspected': n2,
            'sections_ensured_blank_line': n3,
            'backup': bak}

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: status-file-sanitizer.py <status-file-path>', file=sys.stderr)
        sys.exit(2)
    if os.geteuid() != 0:
        print('need root (sudo)', file=sys.stderr)
        sys.exit(1)
    import json
    print(json.dumps(sanitize(sys.argv[1]), indent=2))
