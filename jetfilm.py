# PATR0N
#! 4861f38221f4c26f26622d3edc4366349a8b5d355f37786fdbe5b2378580a9df



import hashlib as __h, hmac as __hm, struct as __st

__SBOX = [99, 124, 119, 123, 242, 107, 111, 197, 48, 1, 103, 43, 254, 215, 171, 118, 202, 130, 201, 125, 250, 89, 71, 240, 173, 212, 162, 175, 156, 164, 114, 192, 183, 253, 147, 38, 54, 63, 247, 204, 52, 165, 229, 241, 113, 216, 49, 21, 4, 199, 35, 195, 24, 150, 5, 154, 7, 18, 128, 226, 235, 39, 178, 117, 9, 131, 44, 26, 27, 110, 90, 160, 82, 59, 214, 179, 41, 227, 47, 132, 83, 209, 0, 237, 32, 252, 177, 91, 106, 203, 190, 57, 74, 76, 88, 207, 208, 239, 170, 251, 67, 77, 51, 133, 69, 249, 2, 127, 80, 60, 159, 168, 81, 163, 64, 143, 146, 157, 56, 245, 188, 182, 218, 33, 16, 255, 243, 210, 205, 12, 19, 236, 95, 151, 68, 23, 196, 167, 126, 61, 100, 93, 25, 115, 96, 129, 79, 220, 34, 42, 144, 136, 70, 238, 184, 20, 222, 94, 11, 219, 224, 50, 58, 10, 73, 6, 36, 92, 194, 211, 172, 98, 145, 149, 228, 121, 231, 200, 55, 109, 141, 213, 78, 169, 108, 86, 244, 234, 101, 122, 174, 8, 186, 120, 37, 46, 28, 166, 180, 198, 232, 221, 116, 31, 75, 189, 139, 138, 112, 62, 181, 102, 72, 3, 246, 14, 97, 53, 87, 185, 134, 193, 29, 158, 225, 248, 152, 17, 105, 217, 142, 148, 155, 30, 135, 233, 206, 85, 40, 223, 140, 161, 137, 13, 191, 230, 66, 104, 65, 153, 45, 15, 176, 84, 187, 22]
__RCON = [1, 2, 4, 8, 16, 32, 64, 128, 27, 54]

def __gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1: p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xFF
        if hi: a ^= 0x1b
        b >>= 1
    return p

def __mix_column(col):
    a = col
    return [
        __gmul(a[0],2)^__gmul(a[1],3)^a[2]^a[3],
        a[0]^__gmul(a[1],2)^__gmul(a[2],3)^a[3],
        a[0]^a[1]^__gmul(a[2],2)^__gmul(a[3],3),
        __gmul(a[0],3)^a[1]^a[2]^__gmul(a[3],2)
    ]

def __key_expansion(key):
    Nk=8; Nr=14
    w=list(__st.unpack(">8I",key)); i=Nk
    while i<4*(Nr+1):
        temp=w[i-1]
        if i%Nk==0:
            temp=((temp<<8)|(temp>>24))&0xFFFFFFFF
            temp=(__SBOX[(temp>>24)&0xFF]<<24|__SBOX[(temp>>16)&0xFF]<<16|
                  __SBOX[(temp>>8)&0xFF]<<8|__SBOX[temp&0xFF])
            temp^=__RCON[(i//Nk)-1]<<24
        elif Nk>6 and i%Nk==4:
            temp=(__SBOX[(temp>>24)&0xFF]<<24|__SBOX[(temp>>16)&0xFF]<<16|
                  __SBOX[(temp>>8)&0xFF]<<8|__SBOX[temp&0xFF])
        w.append(w[i-Nk]^temp); i+=1
    return w

def __aes_enc_block(block, w):
    state=[[0]*4 for _ in range(4)]
    for c in range(4):
        for r in range(4): state[r][c]=block[c*4+r]
    for c in range(4):
        kw=w[c]
        state[0][c]^=(kw>>24)&0xFF; state[1][c]^=(kw>>16)&0xFF
        state[2][c]^=(kw>>8)&0xFF;  state[3][c]^=kw&0xFF
    for rnd in range(1,14):
        for i in range(4):
            for j in range(4): state[i][j]=__SBOX[state[i][j]]
        for i in range(1,4): state[i]=state[i][i:]+state[i][:i]
        for c in range(4):
            col=[state[i][c] for i in range(4)]; col=__mix_column(col)
            for i in range(4): state[i][c]=col[i]
        for c in range(4):
            kw=w[rnd*4+c]
            state[0][c]^=(kw>>24)&0xFF; state[1][c]^=(kw>>16)&0xFF
            state[2][c]^=(kw>>8)&0xFF;  state[3][c]^=kw&0xFF
    for i in range(4):
        for j in range(4): state[i][j]=__SBOX[state[i][j]]
    for i in range(1,4): state[i]=state[i][i:]+state[i][:i]
    for c in range(4):
        kw=w[14*4+c]
        state[0][c]^=(kw>>24)&0xFF; state[1][c]^=(kw>>16)&0xFF
        state[2][c]^=(kw>>8)&0xFF;  state[3][c]^=kw&0xFF
    out=bytearray()
    for c in range(4):
        for r in range(4): out.append(state[r][c])
    return bytes(out)

def __ctr_decrypt(key, nonce, ct):
    w=__key_expansion(key); out=bytearray(); counter=0
    for i in range(0,len(ct),16):
        ctr_blk=nonce+__st.pack(">I",counter)
        ks=__aes_enc_block(ctr_blk,w)
        chunk=ct[i:i+16]
        out.extend(a^b for a,b in zip(chunk,ks[:len(chunk)]))
        counter+=1
    return bytes(out)

def __hydra_aes_decrypt(aes_key, hmac_key, payload):
    mac=payload[:32]; nonce=payload[32:44]; ct=payload[44:]
    expected=__hm.new(hmac_key,nonce+ct,__h.sha256).digest()
    if not __hm.compare_digest(mac,expected): raise ValueError("HMAC hatasi")
    return __ctr_decrypt(aes_key,nonce,ct)

def __unscramble_bytecode(b):
    
    result=bytearray()
    for byte in b:
        byte=((byte>>(3))|(byte<<(8-3)))&0xFF
        byte^=165
        result.append(byte)
    return bytes(result)


_f0fdb30fde78=[181,242,26]
_d8f7ec05879d=[18,136,151,64,217]
_b8a6c582d7f6=lambda: None
_9e5649eccfb4=lambda: None
_70e7d68250a5=[151,173,106,215,8]
_c5f85cd18e24=[124,179,7,151,182]

import sys as __sys, hashlib as __hchk, os as __os
with open(__os.path.abspath(__sys.argv[0]), 'rb') as __f:
    __raw = __f.read()
__chk_marker = b'#!'
__chk_start = __raw.find(__chk_marker)
if __chk_start == -1: __sys.exit(3)
__chk_end = __raw.find(b'\n', __chk_start)
if __chk_end == -1: __chk_end = len(__raw)
__stored = __raw[__chk_start+len(__chk_marker):__chk_end].strip().decode()
__filtered = __raw[:__chk_start] + __raw[__chk_end+1:]
__filtered = __filtered.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
__computed = __hchk.sha256(__filtered).hexdigest()
if __computed != __stored:
    __sys.exit(3)
del __sys, __os, __raw, __chk_marker, __chk_start, __chk_end, __stored, __filtered, __computed
del __hchk

import sys as __vsys
if (__vsys.version_info.major, __vsys.version_info.minor) != (3, 13):
    __vsys.exit(4)
del __vsys

_cc86cddfb82f=__import__('hashlib')
_a2309fc16232=__import__('hmac')
_db0d717d347d=__import__('zlib')
_52180b056678=__import__('marshal')
_77ada1d881c3=__import__('base64')
_648100c5a602=__import__('sys')

_4cc49ef3e625='RthumCFHuQlJZ'
_69d2e1604afb=[15,145,108,91]
_ace3db1c20c5=7798435
_5473f10bfebc='JJqsIId'
_4ea6436ee2fb=3228542

while 505616583302763860 < 0:
    break
if 201527337793673934 == 201527337793673935:
    _44976932f109 = 'QJjXDAtWGZiYavrpgOkQdued'
    del _44976932f109
while 23955255286081116 < 0:
    break

_1dc7e14ca037cf='?RN1MtD_>lglDv3SN+Lb&}D*yqv8M0YlTgzUp+65+yY3%^61Thd=8S&yTseY+HyP>Jo!}fOD+iyFH%R%RcDZVz5bL0hhItOG%#Ip<Mwo%jjM4#(*8A0s}efn%2Jv<e3fj&YG*=@#QFwx(SdA@&=^(O-?X?aolDQ|HDxQ{>@f_c52CqIMU`SBR{llL0;)oP+O2x{Mk!^xZiHr&4vL#!1=h4TF`&Zyx)P9`)teqB`rh@nRCuLxb4y4_)T4Qrh)1-}19N2oGj570WC(K+E84TyM57mM^hfXTM$#=ZM8hBF$lC`PSmdI)Xyp&jTrWOVYa>pKAOOCJRC;nry`m1!CGTv7Z&s+$Q)s;O4SFnk*VQnO5N~|TUk5{*h!(&LqBUupOV028#w<Xr)fh=8WU}g}oA4fa;VuMuh$rG6Tw^-Gox`oDIunONx>rc~z<pM_N)NLD)3}LH1A+k~#?>>nRzeF`tO57$O8w*Z!`T<zn#N~UGY<{iaUH)nX^BJ9+>FJ8YiTqi7)tIo$AGED(tDbSvi1pSwNnW1K1%<%r3LTzs%>TY{0Y?S7>R2@LPCUn<m&4!J^Q0vyr{gY@aD#e25VT<Tego+7h3Zbm><avb<+<EOm{aM(LVI4Vg38dkGJW{&1@h~hmkjnATOwbh3*&w6e${w^%&hEra7@d?D!=GKtzCRZg@Y3Bw9?6bOGn(HS{9(GQU^ErQwYSfzgd1atge}j`r;8#q1SBF~LH8P@|0x(q{H+_irETgjg1UYhHT8d~BM*wx!ICI-In=6J%rF2)+!0_ItQC$*k6;dA1Jpu&RgMj(>166ji-on-j}T1*FmOQzD8M$n1{Zffx8HbQSpYDJ%w<IQ=N8D2g1ZMqyVdY{YS7yo5{DrW~AHg6L^RyV1Tr<UY$@2&8RxE5m!7EzB7<1^}<vS%|v!W7r#Sz<C+c-Q~Mw_2HAl<lK>sHF%Sbvih+(L4DU65X~D4%aae2YA*dnR|y0lt7nhfSG{V}2zAWWo!MJyA9N}I-YMD2A8XKJ-&J|u(;K46mB{Zg;Umx2G>ACtVse9ZCbSy*Qu>sMb*=a6O)oC>sRyb%-ne-ltK(&Na8bGS>'
_e15ab1b36a990d='MCx(-`wG$UKaWFlJc&{(d5=rISyM`6H_C=c-Un!A)x$E|CZ9`BwvqGAU@=88;FcZVRU#k86&lianHzaHUAbxE={T5+$JH>}_uhB|j(F2;fq=W;H$%`=84{@h6n=Zul8^QRQ8q(1i7QXe-gh;*9s?QlI0F}|x=a3pth2Y-H+4Op(E#Z)1+7(+pVkj+B;2d`fabQo%Rj=lfAXtk*9IRuRJfASfCCVun#}wi#+IszRcg^48V00=>0<DlYe6!3{(r2*(z;=P717NQ3O8v5r&q8T(+$ef=bva0%^)Gnp`E&sSziJ#W)$8xY`AXA5mCF_#BlCaTjnt*xQ=P&l#7C-z99vWm$oGH`s-YB=CH>CL1!=uMhOMO9u|f4q2Qu^QjNvta+~udqr*`jOdXNIQp+LsTx~Y%6rl$s_J--wi-sN*H!K{~Sis~<;@JLzG*2-zC`zt`%aHx=JVuj4MrM+#R4)ohd$oqNoMEv?yJ*4W~n2VQ^%3r1w-zKM$f;Q|UcMUvA1sYj+2QSls=m3xXKmxFjsQws17^qtVazn}G1DSY^r+sN}bg8bxE}US^Q8*P*1b(~!O2_sCj)=LK^-HiN8N(1RH^_Q(;QK#~AUnW1C*$ghHF**r{Fq>4u*lGE@cF}cxwcNEg5`IZp=RR?;zn@AB6CkA%-#c%us*F_|9DR}ED9s1Y?pfp6P0D&^J;*hLPF~46wl0Oe}NSQ;TWQoIDdR5hXu6>Y^UnzFX)Y3imK0|6VLmWIHftP$Gj}as2dc81Q|?`o)Y4-@N&)IR4!yMR~|StTF`Sc`s{pad3v?ycH_6FZD^wb7)jH8u^5My34OnbTPtSI|9N*X;}E=h$hzN<t`J<Yj2fJO8Yx1`2Jv3lyE05zgze*qR_{pZ##7+G*jrAJ8akLSkj(r}%>D3&albWN6e8|5;-Hf*`yiueKS#-8Giexil=Z->3l<#2o6Eo50_6k^Y|VqdQYM#e#Qe0K79tCv+CT*e&to-+SO7zn?D(`Ewi2IJ(yY>Ywoc&ucz17_Ivd<6SbK!f`955#Pz@=2b7o3T^EXJIth*>1x8f)tZJ9n#$<+4V1dhsTV(;=B53QSCrBxkq'
while 197186223248059503 < 0:
    break
_d716db70dbd62b='w>|=VdVlqVq(2U6mwz56lLGQT}tY9Rf_)Tj6J@#6x7|r|!CWh4V?<#Y44FSmH6)O*{3QVEyLry8tGr_@-)S+Ps@+?ytK*!E>b2uaaKTn8&K~d3R!JvQg)J;G-hGO$1dY#%=*W?aZh8&G&G{Pc*4qG03{82qR8yze>Bel`^JjtrtPfi4y@Xfo8YW!Yr5U?aHG;uS62JF4skE6%&%|au3np_LW-kZN!Ahz7q4l;mD*PO=w(poM+6Q!!dsfz17xajq1uSbdMjzOL<Aj+*^>@P{M~-AUOy>A)KLFF9||3cyR*q6!XCOR_hKR+7XbI7lH`4RO#ysTk4x-5D9pjYnpZzx#XCapB#Aq2p{0J%I18M{W|66qQFQcQiJE9$&{kX9dkv8CGj_#S~|F08SkkpHpj#mEb^u_!c*FBT?df}Zw&2~y#wQrpJKfySO*N)zsSL(IlQDw)cGhOD{{-E@X2wgkQ{{JZ=*?VDyMi+GIRkf>m<7doQthf6$d3h6(}W#rjNUIta3P?w`Bz|MG-yLPXd~tRDtssxk793TG0^XeTI*B4Jk|LoLMlZ1~c=&FYzb(47MokPwTfzFf<H%N)?h@{IxjHLxc21&-C?G+EuAaumKOg##v>=X%~+<nokW*>xWKs@EVeh-*oHJ<_mG{xpIIA=Qi*s@EuHMSn`mn7DIEU$cI9zwpmg-Y{$QRoI7Q#YgYX@xm}5yrUeq3i^`_!lcxTohoE<nz0xtn0j6Up8bfGVS0MwwWi_D)IBv>41|DKITRbYjXEox3nC&8ux_~qeA7?&)6aFwN++Dm&S#bi>(U&lPD|GHJ(f!4F35F+`E>>e%`|fhZRzLu8V=!C4Qx9Y159JR|fX~0Hb*;hoxbyswf1AWoy1#7N*l8HQOR}%cSa%IrIUJ*emkmG*4rI+;fh=Rc{J7pqO7OlFPL8++r!?G7Ot6a!I2k3)EfH7^B}4X-pM=Phw*#_!|Hpv!@Th5@^Yx7$kz19uS=JZxuGlM-F7EBHd3>W`-QVG!(v<{wpxcI=oetgdl+E7@I~g(<?x_aYLPTE2txnFnui52X9z~}bA`hfWNqjTbz27eMJ)wUG*y&bVeoy'
_5f40267b19f732='2s9Efty`9*u%<rNCai=t{t<qWILh1`3u8#jIe}Bha`Z(Ttz1rcQb#(U5i$$~B}4Q1W6>$NsPjsZ+md~)F3MdzeXN77w)WOIXE=>+RLAIfaCHIrw-G+aV8_TE_ELoItrujq^~owI9mCj*YBT9ot}$!}7%gpo?_a)T12X4p9u}@j80zGHknFV&tVbqlxUClpFdk@i|FQb+SNDR3V?wv8%TXxbaP|m&r=Tt|p#RGT)!o3#9z01aG&c1p%-=hdfuT~<9%q*O?!6tikOY;$R$z3)VqsWwug4dw22t`YIY=~*Ccf#m=ftZD=&j*E!;Ewn(K))jwrp5F9ky#A=vRd-#3Oc$0r4XAU)U3o<GZH*{Hfl6id@S#9aFebT!CtC@wY0X;efizIrxg->X$T;XycDLe6tU@12N6-ZkgBS+)-Us5f;##?~}DU(-~@T<eBi8wLjen?{K`8tUHZg!0o8z9$_IIQ0?n^adv|67#8x~l3z8)!`p?CCvgli`M^-z(|Qax@=Ti6@Wm9{WJkYTknBTOcEVb67i2_<Hv{|))2+WR^j{oWHhD+B(f)PUoSw_CAt#hpuGxt6(88<SHN4Q?;)~4iOM#)db@a>r#4#idVXxS89!Jqyp=2YxNWKnujSvK!^`nFS;BkvQ>t22Vrhy~X|3@$j4AJb*Oy6yqJ%>kv3{!Zcnwv~{a!z&ykl*gjd|)|!p5f9Wx+0*EIy+?)3;4!|UcqKBKZU@HnQadbk#Mw!8yS*%9Ws}Y!0j-10araKECsGWe_#p-T!z#1%tPN{oEUNlrnM4iB<ZQYUy4^CucGBJIfPWJJl4HNp%WJ)F`3Pcb;7t(K(9<{4;Ypuz?A%mDXZG6)cqV!`70_oL_Q#<pg3|sfW9dQ6XerHLI?xe*mmMH|8Cf<SPzfYzZ+GMRWvAa^GIp&K1v}qwHXlh|5fM<1}VjVK)Y8Z@S$xNutf!uAN$hS^a$+0SBYYX%F_Y$D|8uZe6|WQb?E_r%hzU^(HH(|>pke2!sy?N?Wlu`TcU;_E8~4JD0Ay{v88K2_}3~QZud98betvImdRd=DX7^Ee7UCwfr*o8)hS}niMNj=r2rrB_YUqgfDH'
_ec48b4de6d3c17='xK%bt=VZ&Q_)KHDrBj6*HE1@IEa<}lg;D`3|f=)=86kik587<N3B<Wb!>O^;K-*TZ4f89KE2+yu=`WNTi6<+pJGBgQCV-W=uNBzX>G0&T#poP@a2HdX>0Zn{mJyu_SbpF+yAle!>CLlqU`;5?afpuD69e@QG^&h3&>Hftr&JAgzV)57U^1DKl4L!_6D7ccU-<772VL+(#3qd<P&J3SS``pNCSIMVJS0`oyKg&z38m@l#E$kKYq)khFD`9Bw}P4eBJ<^L5I7U;Ft)jROmNem>bpjl)K-Gm<W&FrP+6^`GXvvy5zBB_iQ)wyUu;LFyMT{u4w$n?RPh~4z(SM^FF#a5p1L*4C^z3J9tmtH6J7fh%z0+J4}P&1U+hMYNE@<n4Otis04bFk}{|o#jB#qiKp`)fTCDtE%r3eaEE9=V`_-V1-@8WlRYHG>9yb9MApfgw(aCvD-^C}3i*@DyZo(z0L%bt-N-Vf8*mml?#E~r$EtrDx01;mT_9~Qq&O9Y^6o=!=OV-V2RrJqNAJJwG!}%pe=wjP>2U=YDAfIzL0JuQpn-kDG85QYP#ta&d*=`XAW?IQX}lsnn=&^N_rB7<C&lsSSV!9QaR9SRE@HM@uO&*klKZ#Be=syP5bwBCKp_guS!@|T-`kpX0sAxbFnmK$5pwbRl`D8mswKggq=UYEv+1#G`|QVj-MS$|k4s2>wtnq4b<V-aK+}V3SpLS0FfH%J-u3Lat6-kA)fc*k$@$ERfVqp?Hg~$0+z`2<Ctcqn?9*j)4+u9>L>B2Ju^M1xA7?nIh_9&?cD?rF)^ZV*AD(tizR8CTBCHrYC6S<{Lf?3$a<tn)-HE%CQ%t%pJ1$YI@9zU0yT@{4XnnbFcVM}`OMENuz}<6Hn16_d>?L$1L<}?t*&+Lei+|i*`49(S`<vG5l;<+T6R(GjB6m~JQ2m}GnX&2-wcklFDarTsp~9}@GCm!{o1iAH*#@ic?or0IGm^`dhIjr1`{pdEr7aA6SanscZ-Rcmp*`J~9&Ujo{yP6#`pYapU>p7?%Ag)I@<gPR9}i)NXYGnj3SDOrehb{F6aKq_l}4_Td4%AkZ>wzV^oX~}#4'
_287b225b931998='wmZ@~VVP?cMTI=7s@OU71a+UC%!8yrFKf4Xabe*xno1iQf@p6tG6w^7AoMH66`u5)oyF(3fc@tfbL47@v#N1w3Y7le<4*F|h+VOOwroWjIK?Ct6~mt{w=2nZ!?lNOp^hAzC6U-ZQNPWWF{P&1b22g{QBxnQt=Hnar0pu?y4oMy|V0Vh2s;846oV?5%>la8xbht;^=h+ng%GIlf<v0yyEqqjmN@H;4DTLy*MhhXwpv>3HsH`|NxRx+TWUy^s>Jr;SeDyv~I=4+8xsqFgrq7kM1lyna}T|ho6)_;JQ>G?7pHOe&)q%B%zCx!st5)%93W?j}G(kBQt@c(i2`|H2ED%8G4tsFcO{m)hhgLaTPkg*fZbjHp7`{l%;q%TYLL1Az2m9oiE2AO1OcXv4=<SR+s*A;gG&HitqW4R+)SXwO?WSb533Fe6l>m)%s(s;^E(7KpI99Mt0A0X|FIN4Eibpey&Nwqxk_mQ$dVsjk1%QNekTle}a&A<|q{utm6?5EZUnR+RQJ!xp&tb>+l6S1LmM|l5RRK*G$2Gi1sUdvZBv`p*Y8eNT_Rhb#=lr=)iX}E@*A`yVdLUhMnkovq$rp->71FT8aTG#!~umYh;(jvACDZ&ZRC$-z|zvcZQLnqc*&b{Mx{PAmvA7j91)pU$)VAyH9V`F#T-Ffb;)fQe2c4tl$KM9p+)PE@zqqdkA>R*esk*D#KIVkI0m2N9lO})ql;x9R%qefxP3xr&{0QCGbWw;l2B@x6)wuhf%!}MwfV%Me=yac*KOA$x;&lIhbl`;cZ$*Mf;kKHe1TjDNz45QTQR!sn^v){*gw#Ucu>mgrgob|;K6*g7;hkoic<{Gp&h&7tfilejeID?orx%|T48Cfs48j1Xg_>3>ucSAyZ)N|pZz;awYtPnNAJye2ovuycZ^aU7)H4O(UuC`JYo@a82;*gt{?Ehs-5bxb$F$Sj;c&@*AecG=t*!+PUU&ATXC)|K&i<9JI&%|RQnWyMr8er!=c@?0nx{sd^=gjoCl5RZ?y74-%HnvMz=B>QIiodO*{K!XRWMFi&=LRUg<0aI7bE<SD9G)_o8G$VMqa5Je6BUzVdx(+'

_cffed9ceea00=1780168
_55b02eb74545=lambda: None
_349e01866517='aRoRYKSzNT'
_024f8d725153=3280111

# keys
_b9bba3066c8dec=b'eV\xdb\xa0>1\x0e\x15\xa9+{\xef\x07\x14\xfa_.\xea\t\x1aH%m\x873\x014|m\xe8`\xf9'
_0cd032209c324b=b'f\x13\xbe0\xfe\x97m\x9b\xec\x981\xe6\x90pBJ\xc8\x84\xfa\x92\xf6\xb3\x109/\xdc-\xdb^|\x037'
_340870b1850842=b'\xbd\x83;\x80&\xb7\xa8\xff\xf6]]\xc5\x18\x1cR\xd5\x0c\xee\xce\x19=\xfc\xb4?\xcb%\xe0a\xe6\xc0\x1d\x08'
_a492e4bdb446a2=b'\xa7O\noj\x8b\xeaS\xb4\x11(t8\xe0\x7f2\xf1\xd9\x84\xcaC]\x12\xea3\x84\x00\x1b!\x1cbj'
_93a228203c22f9=b'\x99F/\x89\xbc\x07\xe1&^\xf81\xe23\xedG6O\n\x8e;\x15\xafx\xe7\x17\xf1\x8c\x16\x98\x1e\xb8\xfe'
_b4ac2f0ae0bc=bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(_b9bba3066c8dec,_0cd032209c324b)),_340870b1850842)),_a492e4bdb446a2)),_93a228203c22f9))
del _b9bba3066c8dec,_0cd032209c324b,_340870b1850842,_a492e4bdb446a2,_93a228203c22f9

_ac6c457a3bebfd=b'\x90Xy\x9a\xb7G\xe5e\xef\x9b\x17E\xefj\xab_\xb8i=\x89\xb6T\xda\xa9_\x1d1?\x94\xa2\xe4\xa3'
_a0bcef3fbfc78d=b'\n~\xc7\xfeU\x06\x1b9\x88\xae)\xf3\x89\xf2\xe96\xeao\xb8\x0e\x15D w\xe0u\xff\xe4km\xa6\xd2'
_f9e76718a6ca02=b'-\xc4yg\xbcX\tuKz\xf9\x08\xffj\x9a \x8bc\xad\xb7\xc7-2\xdc\xe0\xd9:\xb5\xc1n\xf5v'
_1f12c861e44320=b'\x99\xa1\x1d\x9d\xa3\xda\x9a1d\x80\x0cU\xc1\x05\xbb](\xa8f\xa2K~\x03~\xd1\xb6^r\x01u\xe0n'
_076241ae6cdc79=b'\xc9w=\x00t\xfe\x1bD\x14\xc7\xacr\xd2\x93\n\xa8\x03?%?C|\xe5\x0cY6\xed\xd8\xa78,#'
_ae2fd08de9c2=bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(_ac6c457a3bebfd,_a0bcef3fbfc78d)),_f9e76718a6ca02)),_1f12c861e44320)),_076241ae6cdc79))
del _ac6c457a3bebfd,_a0bcef3fbfc78d,_f9e76718a6ca02,_1f12c861e44320,_076241ae6cdc79

if _648100c5a602.gettrace() is not None:_648100c5a602.exit(1)

_bd5a6ce2da79=_77ada1d881c3.b85decode(_1dc7e14ca037cf+_ec48b4de6d3c17+_d716db70dbd62b+_287b225b931998+_e15ab1b36a990d+_5f40267b19f732)

try:
    _66c61fa548dd=__hydra_aes_decrypt(_b4ac2f0ae0bc,_ae2fd08de9c2,_bd5a6ce2da79)
except Exception as __e:
    _648100c5a602.exit(2)
del _bd5a6ce2da79,_b4ac2f0ae0bc,_ae2fd08de9c2

_47c97863359c=lambda: None
_04b2bff25709=lambda: None
_ce9716b3dce6=[43,86,86]
_5d571c036e8d=[19,67,195,117,230]

_66c61fa548dd=_db0d717d347d.decompress(_66c61fa548dd)
_66c61fa548dd=__unscramble_bytecode(_66c61fa548dd)
exec(_52180b056678.loads(_66c61fa548dd))
del _66c61fa548dd
