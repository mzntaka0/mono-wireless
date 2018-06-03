# coding: UTF-8
import datetime
from serial import *
from sys import stdout, stdin, stderr, exit

def main(ser, verbose=False):
    cnt = 0
    while True:
        line = ser.readline().rstrip() # １ライン単位で読み出し、末尾の改行コードを削除（ブロッキング読み出し）

        if len(line) > 0 and line[0] == ':':
            if verbose:
                print "\n%s" % line
        else:
            continue

#        try:
        lst = map(ord, line[1:].decode('hex')) # HEX文字列を文字列にデコード後、各々 ord() したリストに変換
        csum = sum(lst) & 0xff # チェックサムは 8bit 計算で全部足して　0 なら OK
        lst.pop() # チェックサムをリストから削除
        if verbose:
            print('lst: {}'.format(lst))
        if csum == 0:
            if lst[1] == 0x81:
                cnt += 1
                printPayload_0x81(lst, cnt, verbose) # IO関連のデータの受信
            else:
                printPayload(lst, verbose) # その他のデータ受信
        else:
            print "checksum ng"
#        except:
#            print "  skip" # エラー時


# その他のメッセージの表示 (ペイロードをそのまま出力)
def printPayload(l, verbose=False):
    if len(l) < 3: return False # データサイズのチェック
    if verbose: 
        print "  command = 0x%02x (other)" % l[1]
        print "  src     = 0x%02x" % l[0]
        
        # ペイロードをそのまま出力する
        print "  payload =",
        for c in l[2:]:
            print "%02x" % c,
        print "(hex)"
    return True
        

# 0x81 メッセージの解釈と表示
def printPayload_0x81(l, cnt=0, verbose=False):
    if len(l) != 23: return False # データサイズのチェック
    
    ladr = l[5] << 24 | l[6] << 16 | l[7] << 8 | l[8]
    if verbose:
        print "  command   = 0x%02x (data arrival)" % l[1]
        print "  src       = 0x%02x" % l[0]
        print "  src long  = 0x%08x" % ladr
        print "  dst       = 0x%02x" % l[9]
        print "  pktid     = 0x%02x" % l[2]
        print "  prtcl ver = 0x%02x" % l[3]
        print "  LQI       = %d / %.2f [dbm]" % (l[4], (7*l[4]-1970)/20.)
    ts = l[10] << 8 | l[11]
    if verbose:
        print "  time stmp = %.3f [s]" % (ts / 64.0)
        print "  relay flg = %d" % l[12]
    vlt = l[13] << 8 | l[14]
    if verbose:
        print "  volt      = %04d [mV]" % vlt
    
    # DI1..4 のデータ
    dibm = l[16]
    dibm_chg = l[17]
    di = {} # 現在の状態
    di_chg = {} # 一度でもLo(1)になったら1
    for i in range(1,5):
        di[i] = 0 if (dibm & 0x1) == 0 else 1
        di_chg[i] = 0 if (dibm_chg & 0x1) == 0 else 1
        dibm >>= 1
        dibm_chg >>= 1
        pass
    
    if verbose:
        print "  DI1=%d/%d  DI2=%d/%d  DI3=%d/%d  DI4=%d/%d" % (di[1], di_chg[1], di[2], di_chg[2], di[3], di_chg[3], di[4], di_chg[4])
    
    # AD1..4 のデータ
    ad = {}
    er = l[22]
    for i in range(1,5):
        av = l[i + 18 - 1]
        if av == 0xFF:
            # ADポートが未使用扱い(おおむね2V以)なら -1
            ad[i] = -1
        else:
            # 補正ビットを含めた計算
            ad[i] = ((av * 4) + (er & 0x3)) * 4
        er >>= 2
    if verbose:
        print "  AD1=%04d AD2=%04d AD3=%04d AD4=%04d [mV]" % (ad[1], ad[2], ad[3], ad[4])

    acceleration_list = parse_acceleration(l)
    todaydetail = datetime.datetime.today()

    print todaydetail, cnt, ', '.join('{:.4f}'.format(v) for v in acceleration_list)
    
    return True


def parse_acceleration(l):
    correction_list = parse_correction_values(l)
    acceleration = lambda e, ef: ((e * 4.0 + ef) * 4.0) * 8.0 / 5.0 - 1600.0
    acceleration_list = []
    for i, ef in zip(range(18, 21), correction_list):
        acceleration_list.append(acceleration(l[i], ef))
    return acceleration_list


def parse_correction_values(l):
    bin_ = bin(l[-1]).split('b')[1]
    while len(bin_) != 8:
        bin_ = '0' + bin_

    correction_list = []
    for i in range(0, 8, 2):
        correction_list.append(
                bin_[i:i+2]
                )
    correction_list = map(lambda x: int(x, 2), correction_list)
    return correction_list



if __name__ == '__main__':
    #   第一引数: シリアルポート名
    if len(sys.argv) != 2:
        print "%s {serial port name}" % sys.argv[0]
        exit(1)

    # シリアルポートを開く
    try:
        ser = Serial(sys.argv[1], 115200)
        #print "open serial port: %s" % sys.argv[1]
    except:
        print "cannot open serial port: %s" % sys.argv[1]
        exit(1)

    main(ser)
