from pathlib import Path
import struct
p=Path(__file__).resolve().parent.parent/'audit/decoded/lib/arm64-v8a/libsogouime.so'
b=p.read_bytes()
shoff=struct.unpack_from('<Q',b,40)[0]; entsize,num,stridx=struct.unpack_from('<HHH',b,58)
sections=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*entsize) for i in range(num)]
strtab=sections[stridx]; names=b[strtab[4]:strtab[4]+strtab[5]]
def secname(s):return names[s[0]:].split(b'\0',1)[0].decode()
rels={}
for s in sections:
    if s[1]==4:
        for off in range(s[4],s[4]+s[5],24):
            loc,info,add=struct.unpack_from('<QQq',b,off)
            if info&0xffffffff==1027:rels[loc]=add
def va(off):
    for s in sections:
        if s[1]!=8 and s[4]<=off<s[4]+s[5]:return s[3]+off-s[4]
def fileoff(addr):
    for s in sections:
        if s[1]!=8 and s[3]<=addr<s[3]+s[5]:return s[4]+addr-s[3]
def cstr(addr):
    o=fileoff(addr)
    return b[o:].split(b'\0',1)[0].decode('utf-8',errors='replace') if o is not None else '?'
for name in ['native_setup','open','openAt','setFirstInstallTime','signatures','getPackageInfo']:
    needle=name.encode()+b'\0'; start=0
    while True:
        off=b.find(needle,start)
        if off<0:break
        start=off+len(needle); addr=va(off)
        print(name,'string',hex(addr or 0))
        for loc,add in rels.items():
            if add==addr:
                sig=rels.get(loc+8,0); fun=rels.get(loc+16,0)
                print(' table',hex(loc),'signature',cstr(sig),'function',hex(fun))
