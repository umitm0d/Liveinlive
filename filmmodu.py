# PATR0N
#! bee39ed8bc2468deb6c3f5a5c488e9dae5fbd643a544810f18f2919e618d905e



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


_0924bf06de70=4853830
_1bff9c871599=lambda: None
_a7d2b8b8f975=lambda: None
_237676ad027e='PwLszBY'
_8a7b1e11a6a3=[112,206,210]
_27c382740f27=[64,110,181,96,239]

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

_fe08d2ced7a7=__import__('hashlib')
_d226932b6e60=__import__('hmac')
_fac1eaeddc06=__import__('zlib')
_419011977171=__import__('marshal')
_55d7d11f7cc2=__import__('base64')
_ab5af6b126f9=__import__('sys')

_ef08a1dd37f4='SFmCFXAAcC'
_c81dd9b46d60=[247,99,159,127,249]
_23cc8ce346c1=lambda: None
_22314cd27108=[151,169,137,120,238]
_bb886c731cb9=[80,8,7,86]

while 110822199822675734 < 0:
    break
while 97745504397686124 < 0:
    break
if 94769817651666128 == 94769817651666129:
    _b943a7d8ce8b = 'fctmHDeNKfNzuZUAckTrvfND'
    del _b943a7d8ce8b

_5047faef4f58cd=';zrwVjaw@;ZY&UefSn%P4<XrEonBfu(^yE5RT^`%uB}P^k6+usq_8sDr7<>#PLw=~2SJO<fhe#wRTPdZL7X`DE`X5j)aL|f?om!IkxC?V5=Q$N&M(%}>gSaX8?g9wl}-Lz{yyc-v%7b$yoDu4{LVqRXVvgf#_*s>nWE|v&^dkeuU(++^AsOgVKgC{?Zu@f<m)^U#YBr<(a$qjM|Z3PAXX3J9y@WYE#IXE68<;2Rg{+zQO_EHf3EOlmH%goqHpUp@~4J=Oo3D}Db)!KFzs_RdETZ{Ng*W8F+3lCFwDF45B`O2uVuRnjp!5WnGmDO?Y`&b+|J>G+{a3kt48SXrnL(PeM8h7-D@U?*rG`<KsNs)25K)ZWhXas%LJc04ocP<EZp@8=?Qn`T64>e=i#xjd!I*73qDP?c70fLhDr8r2k=(@{BK5fvRHa;C&by1Z^#sTH`1d_n}d-3<Ui?_X;F~NNDyN*Jp`fB8y!AIus?<_lA6IV6_4#L3w=KA6>xe?Cr`ZrrKriszo-meFaNN^U%;+T9`omCO7#R2bkj4aTj{IInFXvW-%1)YgHSeh6TPP&u%4?R2U?Lyn84!IVX+ICop80EFEh~R=$uH-Uw?UbapW}LwUrJNi;sj1mI9UP*w&nPq^TT@FuYAwDAI0yVcy4eyfwd1&JTTVU|9}vh?2?&4glSaoN3v~17arzYoyb`$;a`zZTTr&Nu0!y4`l3a$9WwasxkL^?`t!a&*9wGGWLNtgj%3ic8IdhfG&*w@XZwC?*1WTt1JA|4GFlH8>4|H3~?!G&N-R|tHK|8bf^kL?bE+=Z8wx1;<OZdk+UL_3{}P_ii!j%^PcKoM7_uANKeH7b8R7;b<PfpTv<GkWX5<+gn&yj+f)3U(B{;g$GuO>i?{86`X4SJ)N3kf)3Cq%G5EA%IMzt~VE%rfxGos<4Yo0Wb;qaq?-IH)qLzeA1@GFZ+@P?xR)FgGUSl&&P<k9io0=Gcmrgwsfrn&Ne})YtPyPD1Dm0sNMl+b=+x*uo3f&Iay8$vqp4nm{%%ZobXmZZx814{Je+S&gNuA!R-KxQNkg2|gQ*L_SF4CxE{g0E%D#fpJ!>XFaZSUjLp08||aiMuW%(+?Xo}b1}QP81x=e<l)vP5JwXx+FIie#tti>5_YI)ojFn&~|gG<iR9rKVF>ydVWY+^b5>^1H6!ib}L2VaPShD3+oIo-C9orbtUCl^CeOi2f`^diHbXQRd^1{I5`@h4)I=G}$mmRrf|?Hl|}JP|YtbPusWT#Y@+K_fC0gB7}`mAgSM1_r9G{DZMFS(2#s7;H=7T2tnV;E0KLB<`oyt`=a!x0-HLbO<NurcHocy7%siR8R%7t?~=j1c8K~|7eEyhYaxcnPr7Rw(?8Lh{a=f#F(@VS&Q{F~irxyDtcaIK5<%{2*k2u+s9v`!DOxG=3N0`6=x4a)>eaWD(1skeq;$}nV(@RH>-r&}oZkH2?ld%W%}JjVka*FWq(u$ur&+{^`0T<iCPAImR$9{IgucVTpS@gcK93r9JRdny{Q5z0g5-Ed{R?y(aR^3lxp6gApyl(k9l~Vy#a{SZ<F!Q}VQw!n*~)!-?Aue_s}Di-(-)blyZ^>e)s~`=cUH9H^D|p-IzA$<pDnB0yGw16H)u!#4@OJ=3Y8KPmVI%cMXC!-IpV3tiPUJI1@+Ljh3!aAjivh$u^`=ywKCk5n!#r5D`jxpez{BfYlM-Le6?TURV^Ys&}D0_+00%>QMpL{YaP{ZUjoh<53v;LQObf-p^$2?ds;%$Tcm5=dX3rf<m^l(>1R|}E)fY!Bnm@>da@$jfayucgnm>X&%lVdts$RxGA3JLWgbyfe>4+1=g{bU0Z@gJ$W4?J8i<8`5whVYY7NgK^+z_Vl6m<c;ICH|;W&XK(xj<6&LOv$Z~q!L-j9!3WSm1s1;}ytEO>`|G%8zg!z-ENDx@0Z2RPVExFmqsw39~~kZHTfQX>B+b{q2QCIumE{c&0vF)V$>7nqcyoPk<0828`qRhfr&WC5R}$VLE{6k>(`ph0p0J0G3Efu|4>Gt|Dc4nn3hJ)H0J^Q8?)7ZZ*Vt83YV*<)LXONSC1$#w7>QetZX^_qEg2RbG{B=GmVA<$&W_*u_I3%c@hLV(&jg%Vn1rsW&H%bg2(F~9l)*$`}_G&WuX6b&Az-9S#hPy$@5rX*S>jN*w3cnGx!tdDcz9)kI34Um>-Zefr?{=epfM0n|!5zW#{H9>=YY$>=Zu+%S2;ip_rC3VccD_hdS&L;_i'
if False:
    _6ff41a15785e = [201, 99, 223, 18, 98, 155, 130, 158]
    del _6ff41a15785e
_2fb53c53e60cc3='Ru$<w>(G8eT(r*XeR$vwOkoSz(u-s)YwV~=A(dW8thMT)*PF{d?H_}ug?d_i8V?@}yS(c&JU$))BoQDewRL``1udV|<wFdf-bmE!8CY(R5Ry#8lL3PJr5SJT=x}bD-7EqGtk!C#hN7I`Ds2!o159elCuFsY%WFN<D9OsE!Epwy%cyF0JdSH244S;5qKFwO$EwKn!fq5Jp<fO>%AnKH4$Th&Y999eNY$ME*w-#NC7(Ko4xnxCu)$;RN3X37dx|QN4qK@<@A8bZ_l}F9-`43e(t_Jww!-3)=>+t2Fahye0mCI9|Fksw6!%wAP9*dc174yp|Dhk;au$a%0|kpKvX=7zv^M2S>c{z=Sc&-Sc%RXT=i<U<3LC#M6^xu<Tn>1T9M0iSt`IDY&N04;CF7X4j=cnE`~HRyUw`sX`sdI)(PC4|mBodhPDX%~Kh=9ycyR`3haSI+(tYfC1o{B483Hz5LmrxMMMIx$D8B8o>2h}~SR#Q^5jITvpu|5<9;S(I$CD15_E5qrS+8&lp5|$B;^%|e*jFu))9>jk-M=EvJ2e3mVTeU7!VJ99#T49|o=Wf%j?yj&>0fCl?q80%!3Z<P;WZ`pl~tCwbGOHb&Ih>4slnNtale8)Iv)iu7P{gZl0Sieh01%F`mt|i`e{0v*!hrj_m07IUm1^eppM-#D5gd2#he}iB)@Vyz^zo9OJOZnF77=ku9WZcdmMN>Do=JTnr=}v0Z4LxmSFB!y7PUR&|h$QNE3veB1h}_&*y^7EFrzd>e#5%`2$?Yvw<$ww=2xpa>0ZWhxd2$S;_9fQe)q70vlJ6HGL;FtlJw(brt1Gq6a}Nme0tYSl6$NbVNJbaQ@gI>lj*er>25j2gt*;G@+mX^G(sN^gBNl4PyOT^shHmI!g%q1}NFx1WW^muEd3j54SvSF+){d86(UVXDy#gIo@Af3u}*RdX#!wEJ&d0eJ`VH(neWaP@78KMC#Qrg21CESCLc+q$a@EOIgyx7Ck_{B4b+NwZQwh`)MtfL}FfuM>eSeu{DD@?i3yfBZ?S0EjD9E^B!A$1%ku`GkM(NYc~GvaUYyUrtr8@D^ZO}ra{vaFerBxV7bOq5SV=kbP5evQAS=cu(L1%&dB{L-yAe;&&Lo^-Q#Fy;OD}Lp0~1rf+dZcDN>*@5o?=pb(n;XyiIT`b}F?wD-Koi#4#=1#J4jjCE)J!xtXir&|`seS)*_7RR+$B=D%nx;W{`4dR0M|&){O=Eti+A>3wm%^R$ky#3Jc&c+?o6jpVwp)$wfh-Jb~zZ#YQRb`-O`)4SXBNSIggJ$&H9lHotBMJ_0DJg;ctSvD&_3}TBLLjaVJ(iy>7gi<5m#cVP5Ky3QuU@=RpLXdXSV$9<#cC<<41Z=&x(+ZevO-TkXW-co{N{Y{n6}j4L*Fcd{aHxD|mU4f1Msq$lR^zY~AV;b86g17<Ec@~$@*F_$V03iL;x!uZ1=7eyqOb|ggvlSV{}(voobe@N$^I?1xjo@vHcrwl@9S-gH3cdI&2*V4;jqHZrjXD9_^ZD<iJObmmw3+m&P)#y{5D2yL#@+Y28M3W5$$dJ%0>|fD?Zc}aY!tZV8=J&r@~C!!^e7Xp0A8iC<HD$j@uB9THZbt1zS2tFvPhW5U<y`tIto5AS(tSHelFv%%@{E3uL0hz2gnitaUq3_6p7sO}Z=*V^L4}R}&Yxvvt}&Wup-4!}IJK$5GX9K@{0aa7Pvdqs>qy>_K!m1jC|VEK`FaA_iFrl`pW8F8{Lvo!D}ZSNO{z>I1Ck*(g(cGbelE<36tbX^wc)pMxA%<zb4E^mA#-<JnB+JIf}{Do|w%91{cxZwjL>Dq8tF^N~rq=;kdQ(gC@I#jA*@UF5LqQAWa+Sk!c!^ryliZVkh}O)1Ub<LH!FI)_&{Cx$hre}<(4yBdsVsDEnvvv1n5n5F35OtOo$Q7xY;`w9?MZ;Dfhxr9bqy}ug?mQ*~&!!dq7d(<a0rTza%rq?_<&Oh`<8SEu#w{}QoFP)}^E;>#m!uzT@H?y|I!#OEIv%=*&{zE^0uwjPl9#;txM47a52w-Qp7s;vLWy7@*OQZapQxu*IG??>nN;lUb6Ac5F4m-}66%%RSVh}Xd4mT%zm%;VU1=<}WhrNg=#D=T0k~_!m?+4_(m4H!>nQ3_nPXTH<Zre+w|GsgjTbMf?Q5&`)lsjF4&Kvp$0tNfFYvNQ6UIRlOWt%M~mAuQpf?)l;*0BQge|k2P)ecwWQ^?x`6g6IS;N3ptf5a7ND6CECK?$2l'
_a7651fbbb514f8=';j|7+1b}d1&Sgum6fC4(lzvV8fo|B#mu`5auxi>43D{1sb4N<K^@Zx4=Dezxa47EiNe5XjL@VbjyTQU+nk@$y)li&Fwx-Bb{<Sc@JEt)4-^rRMbmsy1#~i9!)8vX;Js5o+PZ6MIQp}LL(s5iTHVtekbJMbS+|z@6Eqz9CKKT%XO)%`)_3^`?x@G8>Dqe8zg~-M3wHcz9%3D8{AVqz*yPuB;q8*5O(rU-b5EASeJ?2TP{e>$`sx+_WJ#gUx7KmzLz~2|ig@SbA^XBwE1!PcvD;`6$%nTG|ASuJnF;Y6aXpe^$is$V1SK7)ti^QQTmTzknhXb@neF#Jb)e&Kb_l}m7j%S<G(VwFmhWgM&8aHVODjA#B#wTNu(3A}t_l*%b7vzv_vvvykr>%AZ!9K(SgsM9UYU0d^CX+x$>X~+w0J9{@4F)QxR?$#f1jbcltxh@hge?7A-3>O5kg{Ibjz{Y_GtL&l_qa~y%N9Yg$N!5!8=m!Z%H7aP4jevA=cM}dbHNhP1zM`$L5GPAg71GboavHQ+!Msr`%D~n=T1pWn+2mL6QLsJ5_d#Tlqk-HweK8jyj;#_51dk4mh9i9VBUjPd6==GzaAwP`0c=Srq^hMD~9HjONCKkAv))$>rLwq*SGkhf-S})ERek+b{`2?6SoU(G<+JHlPLe3dq8BLtO5$*OGl`bP%Lg6k&<SJ|1+DCTFIg>TyUU=BgjJsZU1hF;G=D(kErbMS){9Zp|VaNRvezbnH?MeAa<-f07H{&q=8jWw>}Df#3G~KIdN6?N;Sz#J?Q`Tsi%@B5-00`s8F_o{p}A>sZE}T8{&|3{W1c}0f)xf1u5E^)USgjO%1gsF{634kRgsJjaUjq!j=Oz^&6;Z5pOlefyusdTi*%EZfHSecwjyksI`)T(*!gI=@V<BC?2x0e|6L>gUZMnHC@B>bB}PP4nuruySAH&dpjJYBAc^{#{WxS970fuq${UGtw~7bS$Ty&*~N^6PrOu)xXWy?g$lk7kg*j9_nwA8g*==e`hfM|>5&nP!K7!GFHxHd<=%5na3C5<Y-KtgOUw#D-yle)$<BB}eH^%)*l@Q*t<uhlX&nORDOog%QI~}jdhSg@QqF)NH1B52wa1<v0jZ4chu#J~HF|Jm?gAJ%Rq&5xEh|fUyiymvm1}#Y|AzprPBIEI@__lL9+wnGTK=%<VhV-=lC1gE)~1OcPWC!WO*f77<9vd-L)Z|}uXg2c&GQIcpYc>Z#S)yE!%jPOr^c*_4>#+9_O)Z?%+6FfML)Wz6yoRId;41F(fWN%C(xYcS=3+J(d=VZ7{iqAHoOz3M+W#0h&YPY(tq}#T+Rc}dSKY?yR*XlNLnn%))P^QY$g)1mRhl<7}l>&A`%8uBz?QvqF!CGamPXk4DF#w71$`~I<TeJ_c^R)YZ$@7YgIY{ecQK!xO~M~0KD>Aey$0&uQt%v^yfIwW38J3?DQ=Q4rGq<gWODdQ~jk%O$j1q%0I%zwoaerXZp!-J%x*e73RXf^PIu#(|qE3mSkGu-jv0k0t#9=2X;c4*0(MW_(Puevc3UA7V?HFur2e00ko)G`62uj7iF`c`5ze}wwH!s^6{HxM_UJx!WSh?e6;KjWQ3x&Mj4s_T@-o@>DllDks|vWjhV$p7qJt?muWUHC;<w1eE6YyWU-lwkUt?Q#GAjfEIixF;xz9Xop$e;gWOO>5qMqAm3<h4EJRxuGJAL0smHHK^j4=ux>l1wituDQG*SDtR2^3;&Hn~xH>`K-09xbwQ2?!lH*Vl(hoVe=T)p-LKq7MF!#VT9LMF@0<k{XTEWDoZGZC}vOZ$PAUTh@dXPI^0(;e`-c@D{Pvxxw5?pK0e%*PfUfyJ5$mgA?Iki>ctDe_n+2E5(?B$9|wWP}2|>I3!%|LIx7o$?p9@iKe4&61SxLe-upim1*7F#nry|J@@d2<b9OBte9j1$KqGmhroVzRJ(&O<}<s-U?kF%<VuhE&67WoRT2nIRE&*`KK_0SxrQ<vgN!fn|iwh^$G?S&%5D>Xx<Aj&Yp1esMZiq1^<ReZjQIZHni*F*hN5|sHkSAb-B6U_8*6v_BefjfrC8y>2?ReRSNk&F2MJVio||6*h>as___~JBsBb}d3ngHEi+D!>?~0un3Tb!c|huQT~o24T}j^l*sHjz_>!O0@wj+etfGphKPMAz;<*qSv+KCJm%U^oM?1CVAU(2a=|0ho$aR&)ma*pNbCoDe(y+F%wGhp+YWgcNPf)4tfrnBoU>tSEnvN?pubR#~'
while 261893706759731714 < 0:
    break
_6a60c06e6671c3='KM`R7Ky^EhLo^&wXDuWl7`$uLlhIyat1z=iW3;Wd{iI!S)wnn=n<&H%$({Onv+pn9b|{S1jKpc;t`4Xhb8q`SP#dR86L@MO_I)h&fDEz9D+WuQj-i(NXeQYiE2k{hl4!IUYg=O{MCp6uqDl-@l}d1BGJki6^4_|T+Xlg(&}PAdLs19*RtcoBG7cIfZ5TD63xp^U*RQow03$Tf{q&VJ9ki%gzeCKpZ_oleLq3pM9}Gu3$K_dMLfURZkm5mJa3n-P%DrxB!D(8cSt=2`pQFbK>qpb@r|`yzG9zrSmbW90R!!IrlopMWih2E=WHWW9$pPZz#BZ0+U+0BE3Llz4jIEYcozOA7tZc(v4fujYYQ4aouF?4S?N+SmNl{z-#K34$?CbThG_LJZh<<{FOMp@>@SO{RBKHN3FgsQkcc6gx++$se5>|0-BI_g!p3$Od*4p~P)Yq^~SOY-+%7W%5Nr>}j(MI6)t-DT&uHuRW&jh*l%JCcn_-%Hkap+D~)a7>v`|ud2QKmZ<sedz=2u|~laG|jB_@fQ)Pt9wPLY}Jq-gLp}6x<z>wA>^_w8bzlDQ;o(b6w!31&oI?8F4@e>Kf3PIfalD^&;s3Z`W^Ll`ZCYa@z<uCXG<*GN3ScwUvCZn0l6AF&*&xk^A{E5CA(yw4nEE0?e>!IAkBQ=PmKbXA!nBtg^@oix=4fx(O4kWCK*7;{M`S(j<yd{g+7`A==yjf5PPRmVTJ8lK&)-OD@t@kO;}l^bX21Wx@i#2%??TB@FD;xe&5x<nXf~OZK8iPva824Gw7nC45Idv5n_l8x4s(a_QJ~afckT8r6PF0M63a1(H$LBwSfzYRxax#BvB~+;>}R1TxQk4$iphxzPW^Xa~fyH9a<LcEojPZ$x2DZP8L;D<FA`6|MEw3Jm)1-f2EoiBRKl%c9)z_fk6=5SfR1y5;kb6P)=C_oPl4O?VHY*)7^^)0!0skgO7|FTOm2PX2%!j;Sbd2{G{LDO>o5YbIl4etJL#uW;XQ0S&Rg!z*8*C5jyS6;tuT9J@|~;I`60oeHrRjpR`a-lc2YEulPB2u1=w{UCoMcEG1b;S?XZ>`slONSM~8LtMFIsc&$76oC-y>$xVo`M35*SFG{Iqj3U;M^X%{+%+ap{-+Dwxm%f*1jrmMoeUCh7zu`d;NNCmalnVeicY?6Vq>Y_wD01ZZANMudrKj*m0743k!;vU%O%^th#(6q7FAmd89#00y45w{rK1g&^StrwO5+Fqm%Uym?_}s_YmV^bQ=+7-_DZhDjP^xbsHSotXnWl*kwnpR#W>7RL%t1)h-_G(0D@j<;YAG`Qa)07nKZ~gnBYp0<&Vm!^7d}*+~hZlWDq?dz}v1np6>F*uOrT(Qq*VVi|;ZEyh%{&go(g-bjm2T@^Pn6$A0xKu-z<0o)}p-D#R%=xa8v0%a=+dNvFj;DWlWbsX?V2ACc@N#or>D;&RVdez*3Fn9ud<^~>A?iTaF3Pjr8uSy|juceNY@#V=nGVrUl6Z2vH`<N+NsTK<6Jl9L_pF8NtN*L4u{AmuE!YVUOz3i>*;`n66u2xAYQkuq5Rswz6lLBLfhBo{nkV7M`*UuH!b1rDM-b6VXsL8gsY1qsBc@Z1y(fDh`mA4roZSoA_^88ki+jw#>FuFEyiMUQT#MiuKg<)MhmNE-i&zGm%1y>@PP8deg&=$F+-LF5_k#0>X?u|f4;k!FdFzW72?6*|Gx_mQW60?-E{bJPQPxJpj0Zq&br#G8LCw;9-$I~xzE7qeBS)=HGcQp$Jzmj{+FwojpXEw(aNDjwhmP^v@a<1%^wOp*FDM7-(rj8{1u9;i^ZvtCv!v9d)mT_dL1tVSyR@zU#>ADG|$C;e_Y!NvnU=N!F^hvXdXXV21~Ggh25Y`>1D?h6F<!`YaK8Cg4@3wQ8YGkle{HH*}nx(h`q=`h%t6yIg@C7Ynncf6_)C!CCECJ3Ats1kic=H&^MIi%FV#OTg~eG2`4Iv2irKK#gPbr5?4TF;{J6?p|og@<#JsghiBE4YI-t)QuyeTo`g0~JDFq|*FOwNBY%5dGm>3wDLnxen{U&=`&x2OIxJNexKie9>KI=tu+M!Q|TlillAoB5gixp9Px#wgeaJP2{zq)j@dwp+3QFloJk8LBG<~wEL&_843`!$3IW*uQ-AIxfuW8Mww%aH=fVx8DN#UaA@36H=(vwd!-YRs<x}`R*W;TPVcHIoLJX&4AjN6r?7ETKV`8jT-h%L7SjF8p^h=z^djY#G;Q@<V+({b'
_f2dd5dc827fae4='p++2GN1EYVCalbzF$(tO0&Oy6eZw_`I9usaPNuPd5J>h(*0GYvKiUoJnhhc?p_qT}z#if0Ga~C}D*dVi?L@?fCOO6duDcRPcu68TGb{YX<pg1vbLBvE*R!-T8rh(dp}{drMgzsK=pRQ-LlSO>$!7DDPGl4EYufh8zx|>WajELJe-f_Ib(1gAdxEG#@kQ>DK+clv|IiiiBEYhrM>2E_?g}^_K0%wXPZmYO5KJsy+CW7i43vUH5`!f_o1$L<ega1^R1$8dDH_k|?RRf&M<(TAC7k*yl8lNIx2D3b>Gc_|L8Ou7auDphht;(>3Po8(<u1bcs-1&?p@cQ)FU;86P<kG)Hg1NnflqDPic8q|EaiR|-G5bXUg6CvzW6ryp75OC=5|YF+$o(BZr)q-)h`JUba#6upc<SHETCM&fD|N=GXYT$`SDJthH~JjdNaRm4Nf~fF?=Eg3;3N-Bl_=Dtt>^^yf*v_&9<tbvv%LDb<m6cS+!zPIm9Z7yzpv8dC5l}Ti~ox;X`7$ji4^bXEbbSRc4nbIBE8g5YT!?5lg!q>dkyGEx04eV2SPF<FFMm-^QR?7#WI3gdYmsCO9O1&O@vC<%jdGhpGX3nPt;0<#k`qrxWv4Fw1IJFgZeNSWURYSH&E)Jb0W4E!+rh*B^?On$a)AavCY;*q*7w@DwEn<KDZcP?77L4&P6+)|0sOoOxBl*(OD)>?f5@uTRtb$`PHoSA=<Cd0%T}>=JWaUqWU(N@}AB-BpFB5X2r7ThozRtw>6)71gdzvO<B{^sj*8uW<EEcKBo73QXYb2<p??Vl6bz`;D_^G)46zp#6=CI6=9CRj*>y{mKLZGaz(k$2=+1{gzMQTVNOthoIe`8|&zW@dNFaM)YZ>IBI-sp{Yv(exa{SB{?Z_DOGMnmNnosrd{~hx^+4=#Rij!PAa(p`Rljac}LA?xgU6J^9cU6{sIj!`N4305oUp~)01{d^}6F9I^uc2MJ>^#jki02LD(`|DcNoMTWa99z?{HJW^mbrB8dVM&%VfxF4CG-ap!wFxEx~oddy}<(7lJg7GzN54j9=`rT`S@8dPY?A#lJGRGC6d3*+{s-pAQ3R)W!c%fX=@r?ku-72-fBM6v36k^p#Fc!_8)n8}S&9IPAIR{VP0wrC;m9TLaCJknG<{lV?RUUntP%jv(+{2pb4Hqv|qb`N;n@JEzXr{sySE|wm0jl59&G)E!QOn#cMX}c<>Zw^1DW2xZ(Al|SA1{s6BN5)nL*86EwBX2I=2-FA|+&rU+d@QbHJOGLW+sm>f$#weF|2C_b{)ul@SF^ZI0Y!;0#2`uiKqtfF&4r(aHPX?EeN_~mgp?x+?jMWBqwcaY*+PmnWasT|i?XS_SPxP;%lI4HsD%ivlpW01nTKIP!7k@^7K;aR3Oj@>cu{8Joi0dLf9~L_zg&<fTGw8CM>^v72JEqY3isqVG4x$M!?^<N=<P)G*SS2eHI?fAl6_ZB%mo?yFIWt);(L;YE*utRKdn$ZbD|FiX!oe^3ttu8v?C>1*H#|VCkTGe+)%^0QWumfCr<<5=qA^y=B$+xnr;UCb)S7-`kx0~Wv<oN5ek`g)|HxnPq@s;%xY0KqKRz!1i%j%3ezU0?4ELOLWcI4H#1t}QZ9yNuvZrQnIo|A(2$}8a{y7-KE~|LQuwk7eK)I*a1`w$0;RwjdGat~u2fPOXGQ$oBj{XiuAzfL(I}!owAvN$Zq&!{5?GBMw_kZ901fr>1_&k)PE*sL{nf^#jH>$X(<w?KR1OoAtYf2_dYJXEzmpsYM8eN^OM-Ju%44E|8tP?P3|sm+WKnCZS2J7o>pG)-pqOa=&V5`IF9_A(G)XW2(Vfx@S2?l#JrJY}1!hLHcvPe+x7W8b|Nj%4kctyiyjqH9b+9gx?My;nMhPg3w@u<jQUz2J5=PBuQ$ZrLujnHP7dMj+NR7?l=hfpP%aMP|cn$Ok;>XHZc{t0Y5v72v^fT~YrNDBOX9WAIMAjwAlVg3BRE#vhd$tXOqUE>+XX~Y_rBlxLzO3$JE`ZV*<?iaCjHg!65;C-=#z)O7Y+Djnn1xE<OJM_Cj8TW^fAK(y=J%N!eOwDi2e4?qY|uD5Ir~duSGWXK#b5{9S+74Am)~pMT;}dXbPiZZQ4-9Mj9N?{rwUK)2CI?yaeD`7ca_-Yyldp(tGiBP2OQ0c`)ITa-?X^3Q1A_awq`;?#9y#YXoKE3JkUWHJGVM2nxyjpEDON93)Mlr@B1VPclJ<zXGIqS_<08Bi~PhlehDF_'
_23afd29f622cbd='&r?-rkX5oIBZ%S61uvNOf|*w^AN9W~BlEK*M?ldMc>$CMu=xRRFI<4G1|LZnh|8tYtO8&ghTGnXeI=T&_*U#R*X9v1%k(S%jV%IyaiBMQTTcUu^%6m)%RGFtni9{Ox6-URFA=vU)YDX<g^7W?=o6<?w7J(dPtwrcpxI!CQS!V5pJ4K}jILm+-f%~m_QCf9n2=l1osbsS3rN?GlO}fc09<O&&>awNGpc|H<B*`2TP`U{$^Gr6tG-|wpvp~w;7vJSgynQ`<CwP2sX~^|xO}-Ld1>&grDKyWb4;=cwz9-rhuugOEa2E<fmxiylKtY{wL$@%7hQ6>;8O#2*2ygd1ah%3X5uwjg>IFc(QEv^5b8*T<@PZ#X6P5wDr?A8UQe<|7TCySR5wa7dpTyf&u^tl0);5T;6-6Qm-&C49dN_!$3LE_UZ)zts4v+o)ko7LLtQHWPfo5%yJK(VKV0ta9$)!_&y2F3nun==(6YFrCt`gAFa`~O=Pa}6QDu#1H30CHt5nrLH|4jImvEP`%FZ*JUT~PuT&<F*9JxC}`VtFmz|L%F!B_OB00*e7k;UWq&cN&Y&6A+_!t`1iM%WlwvLsq^HJAz5j&W=4*IaffwdhB>^UB1LH22(2*CgUE5~o|6&=J^QY5n6|`_e>UZR5`cccdf71c+Tp4mwDd1Muk{dh{+!k`zUDyx?uUX)$NJ98|+s<*!Dr4it*1pTa+Vlp-7YA3}Acq?jv)-hI{-HqdU}XOyLGgqHrxQX7P|9(4%=UGf)>5@|9@pHR7HnvIh8?QDw|>CG3pZW}QU-Q_|4w>hg~g)GG^3*cSX?0u7myAWjtw;(Zqsuy7|VK$Tk#G+x7hDmqxKSM~ThhPV)t=xOlVO7aZId#RLo|Z351pdAF@+)##^*V`4yQ)&WE)7-cZAig-@?Y;I(<gCh&+HnM3z&RlY9gEsn{avHmEc&#A<p4;qZx<v4ng;mQrjf2zbo7sfmPv{36wZdsPr|xI}E4FPRd7j1=M?^AO2czN~FE?d#MOC_vOKS*5b}~aTf2JjNQYx)3`r4>ojaT-=Ve#UVn(ThQ<XDGIpO`bVT>{Dv3$TLF?7TKC06HhupIKa`jAmv+pMCmH#duYKo(<BH%wx+T<sjt|v&1_26KF=)?It<QHmr*+>_qX{Y#vG>$>3!X76VyLodbk0;fd?`g7dGk*Hg@q<Mo$(i~ifA}eg`_ym&mGKvN>Giu&a2%K#0wZ$(w6f6wAh#=kj8NS|+Vh>)!0|f*82|D+UzNg@WFP-^LulCCXQ;(?|IVdEQI=|P!Z=U&w|SPQsQR}GODV6o2Yxvq90NFZ8u=;SZe9e_eE=u4RSaW(Kf9#JR^-DjqT~qp{S0<G1P<As!e!UxXo*ZtXG2HB8ftXCt;OR5U1-WJM*_~z<|v#ndGuen^AEm&>Qp@32_F`;?1cN4%lWXDqFR+Ak9?uAv?&+=l1lOMuUT2PDX_9%bacl}R@Su$LuW`ZVoS^ohXpy5%vl%P=m)eg|I!Ipl@D*niiqZVz!EW@sO~A##^qLRkU_gjrJ3n@k5cAI*3h#KoQ`buAA<lr;hbJNyz&{&UK9!^PW?Q80)nQrwx)VTG*j$Xec!y2Do3qG@bb{BO{KSAdOo5x6oemU`G3fOnpOAsCR(+sQemt-#aa`+eJCLHs#15n_9&S&S&b|mJ8hFg@R}0H(Kjc^lYR~gtx%{sk!9&pf+0Tcd^}}o;k^W+0u~R}uZduzu|!CQy)mBD%kYM-?B0<d&PpsN%lnqw)m>NzS8qS(w9nh*XgcO|s(@0<ce?cTfe9o=X~!2Z3Qc{_HHpHS8YK0+Q^F^p7SeFfP+C$)nIWI9b5+Q>FBv_Bd#QXz9yjZ*ElQ5!YhP!jkkG&jipwYL8)SC$d6zg}be>6_?a^i$Gpi18z0WjkQl;>Gm1WRcti8^uSV7$H8xwXOTc}H;G`!DAIw4@-AENdW?lzC5zWR2uvaIr#+a8mp^54uUd;gmz`y53RBXh+7$2e5TLq_hl3DJwQ!14~arj!|fF{WU?DQ`$~&X%<JUVxjLL1lRQL~I`vI_`xiJSd9o%lxmNCI{#R%OY26%i40HA2OCY{A`dLqTxWf(eiR6^(`WjaPm~0jgu}eZ*>F{iL(AO4lOQ{!^8^$BG7D-Rhr@+P%So#&1cc;W2lexMAw4Y(&ty7e^djRg~H~2TpDF=?xd4$=4nhpI`V8wkVidzKCeogPar7@L2zdJGDQ3DEpk;6_%OXK`@APiU=v4im8B>0A4kY+(95rb&w~'
while 746287479163810167 < 0:
    break

_cfaaadbd7e08=5837032
_17ce04e1b92a=lambda: None
_9ad0ab8eed8c=1498643
_a4eb4ee9cf4a=7028923

# keys
_240612f8658960=b'\xa9\x85\xb4{\xec\\\xd0p=\x0e\xa8\xa9\x13d\x9d\x14\xe4UW\x82\x1a\xbb`v\xe6\xba\x8d\xcda<\x18\xfb'
_955dfdbfe1e856=b'\xe7\xffY\xff\x16\xe9\xa4x\xbe\n\xeaa\x07\xb6\xb7\x90!\x84\xc5^\xfd\xa3b\xbc\xa2\xa5l[\x11\x84\xa1x'
_439d85486ba436=b'\xbd\x9c\xc9W\x93\xb5N.\x9b\x8d7\x1b\x10\x8d\x02\xc6\xb7U\xd8K\x19h\xa6\xac\x88\x14>:a<+\xb9'
_21ce073eb700de=b'\x05b`\xb7fc\x94\x97\xb2\xfb\x84\xb1Q\xb2\xea\xa0\xd4x%\xa7E\x0b5\xbb@]ES\x07hr\xe2'
_ac625e1abe3189=b'\xc8\xa0\xad\xfe\xa4\xe4\xcd\xd2\xcdB\xed\x14v\x04n\xf3\x18!\xf6l\xa6s\x05i\xcb\xe94\xbb\xf7\xec\x83\x9c'
_7b3a45804e6d=bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(_240612f8658960,_955dfdbfe1e856)),_439d85486ba436)),_21ce073eb700de)),_ac625e1abe3189))
del _240612f8658960,_955dfdbfe1e856,_439d85486ba436,_21ce073eb700de,_ac625e1abe3189

_871d33ae41e0a6=b'\x90i\x8d)\x8aYb\xf2\xcc\x96\xd6k\x07\xa1\xce}\xa5`i\xbe3N\x1c\xb7\x0c\xce\xdf\x90\x85R\xd7v'
_4695408e41b5c2=b'\x1c\xd2}u\xacF\n\x13O\xc31\xfc\xe5\x11\xa2z\xf8\x9e0\x923\x15K\xe8\x0f_\x1f\xc3:0\x8d\xb4'
_a91b1838d99194=b'\xe9\xc5\xd3\x93\xa3z\x1b\xe7\xdd\x14\xfc\xf3-5\x7f<iQ\xdb|\xf1\x89\x07\xfb\xbb\x8b\xe6\x92\xca\x90\xe87'
_1dd6d3e6ffa150=b'\xac\xf7\xa0\x1c\xd1\xd5\xb8#2\xb71\x92>\x01&w#\xac\xc8\xa1\x01^d!\x1cN\x90\x9d\xd7N\x0f\x93'
_c68bd3f844254e=b'\x87\xd5\x81\xb2\xa7\x0c\t0\x99\x7f\xca\x13\xcf\xff\x0b\xc6\xd6M\x1b\xdf\x9a\xa1je\xfcjKI\xcf\x0cw\xb3'
_d16029d3f5e5=bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(bytes(a^b for a,b in zip(_871d33ae41e0a6,_4695408e41b5c2)),_a91b1838d99194)),_1dd6d3e6ffa150)),_c68bd3f844254e))
del _871d33ae41e0a6,_4695408e41b5c2,_a91b1838d99194,_1dd6d3e6ffa150,_c68bd3f844254e

if _ab5af6b126f9.gettrace() is not None:_ab5af6b126f9.exit(1)

_02bcc8b659e2=_55d7d11f7cc2.b85decode(_f2dd5dc827fae4+_5047faef4f58cd+_6a60c06e6671c3+_a7651fbbb514f8+_2fb53c53e60cc3+_23afd29f622cbd)

try:
    _8bc34bee8d35=__hydra_aes_decrypt(_7b3a45804e6d,_d16029d3f5e5,_02bcc8b659e2)
except Exception as __e:
    _ab5af6b126f9.exit(2)
del _02bcc8b659e2,_7b3a45804e6d,_d16029d3f5e5

_9fa7d50395c4=lambda: None
_e64f53d7cfaa=lambda: None
_98f0407a44fc=7689274
_4843d3d2beda=5466655

_8bc34bee8d35=_fac1eaeddc06.decompress(_8bc34bee8d35)
_8bc34bee8d35=__unscramble_bytecode(_8bc34bee8d35)
exec(_419011977171.loads(_8bc34bee8d35))
del _8bc34bee8d35
