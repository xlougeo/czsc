# coding: utf-8

import warnings

try:
    import talib as ta
except ImportError:
    from czsc.utils import ta

    ta_lib_hint = "没有安装 ta-lib !!! 请到 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib " \
                  "下载对应版本安装，预计分析速度提升2倍"
    warnings.warn(ta_lib_hint)
import pandas as pd
import numpy as np
from datetime import datetime
import mplfinance as mpf
import matplotlib as mpl
import matplotlib.pyplot as plt


def plot_ka(ka, file_image, mav=(5, 20, 120, 250), max_k_count=1000, dpi=50):
    """绘制 ka，保存到 file_image"""
    df = ka.to_df(use_macd=True, ma_params=(5, 20,), max_count=max_k_count)
    df.rename({"open": "Open", "close": "Close", "high": "High",
               "low": "Low", "vol": "Volume"}, axis=1, inplace=True)
    df.index = pd.to_datetime(df['dt'])
    df = df.tail(max_k_count)
    kwargs = dict(type='candle', mav=mav, volume=True)

    bi_xd = [
        [(x['dt'], x['bi']) for _, x in df.iterrows() if x['bi'] > 0],
        [(x['dt'], x['xd']) for _, x in df.iterrows() if x['xd'] > 0]
    ]

    mc = mpf.make_marketcolors(
        up='red',
        down='green',
        edge='i',
        wick='i',
        volume='in',
        inherit=True)

    s = mpf.make_mpf_style(
        gridaxis='both',
        gridstyle='-.',
        y_on_right=False,
        marketcolors=mc)

    mpl.rcParams['font.sans-serif'] = ['KaiTi']
    mpl.rcParams['font.serif'] = ['KaiTi']
    mpl.rcParams['font.size'] = 48
    mpl.rcParams['axes.unicode_minus'] = False
    mpl.rcParams['lines.linewidth'] = 1.0

    title = '%s@%s（%s - %s）' % (ka.symbol, ka.name, df.index[0].__str__(), df.index[-1].__str__())
    fig, axes = mpf.plot(df, columns=['Open', 'High', 'Low', 'Close', 'Volume'], style=s,
                         title=title, ylabel='K线', ylabel_lower='成交量', **kwargs,
                         alines=dict(alines=bi_xd, colors=['r', 'g'], linewidths=8, alpha=0.35),
                         returnfig=True)

    w = len(df) * 0.15
    fig.set_size_inches(w, 30)
    ax = plt.gca()
    ax.set_xbound(-1, len(df) + 1)
    fig.savefig(fname=file_image, dpi=dpi, bbox_inches='tight')
    plt.close()


def find_zs(points):
    """输入笔或线段标记点，输出中枢识别结果"""
    if len(points) < 5:
        return []

    # 当输入为笔的标记点时，新增 xd 值
    for j, x in enumerate(points):
        if x.get("bi", 0):
            points[j]['xd'] = x["bi"]

    def __get_zn(zn_points_):
        """把与中枢方向一致的次级别走势类型称为Z走势段，按中枢中的时间顺序，
        分别记为Zn等，而相应的高、低点分别记为gn、dn"""
        if len(zn_points_) % 2 != 0:
            zn_points_ = zn_points_[:-1]

        if zn_points_[0]['fx_mark'] == "d":
            z_direction = "up"
        else:
            z_direction = "down"

        zn = []
        for i in range(0, len(zn_points_), 2):
            zn_ = {
                "start_dt": zn_points_[i]['dt'],
                "end_dt": zn_points_[i + 1]['dt'],
                "high": max(zn_points_[i]['xd'], zn_points_[i + 1]['xd']),
                "low": min(zn_points_[i]['xd'], zn_points_[i + 1]['xd']),
                "direction": z_direction
            }
            zn_['mid'] = zn_['low'] + (zn_['high'] - zn_['low']) / 2
            zn.append(zn_)
        return zn

    k_xd = points
    k_zs = []
    zs_xd = []

    for i in range(len(k_xd)):
        if len(zs_xd) < 5:
            zs_xd.append(k_xd[i])
            continue
        xd_p = k_xd[i]
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        if zs_g <= zs_d:
            zs_xd.append(k_xd[i])
            zs_xd.pop(0)
            continue

        # 定义四个指标,GG=max(gn),G=min(gn),D=max(dn),DD=min(dn)，n遍历中枢中所有Zn。
        # 定义ZG=min(g1、g2), ZD=max(d1、d2)，显然，[ZD，ZG]就是缠中说禅走势中枢的区间
        if xd_p['fx_mark'] == "d" and xd_p['xd'] > zs_g:
            zn_points = zs_xd[3:]
            # 线段在中枢上方结束，形成三买
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': zs_xd[-2],
                "zn": __get_zn(zn_points),
                "points": zs_xd,
                "third_buy": xd_p
            })
            zs_xd = []
        elif xd_p['fx_mark'] == "g" and xd_p['xd'] < zs_d:
            zn_points = zs_xd[3:]
            # 线段在中枢下方结束，形成三卖
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': zs_xd[-2],
                "points": zs_xd,
                "zn": __get_zn(zn_points),
                "third_sell": xd_p
            })
            zs_xd = []
        else:
            zs_xd.append(xd_p)

    if len(zs_xd) >= 5:
        zs_d = max([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in zs_xd[:4] if x['fx_mark'] == 'g'])
        if zs_g > zs_d:
            zn_points = zs_xd[3:]
            k_zs.append({
                'ZD': zs_d,
                "ZG": zs_g,
                'G': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'GG': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'g']),
                'D': max([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'DD': min([x['xd'] for x in zs_xd if x['fx_mark'] == 'd']),
                'start_point': zs_xd[1],
                'end_point': None,
                "zn": __get_zn(zn_points),
                "points": zs_xd,
            })
    return k_zs


def has_gap(k1, k2, min_gap=0.002):
    """判断 k1, k2 之间是否有缺口"""
    assert k2['dt'] > k1['dt']
    if k1['high'] < k2['low'] * (1-min_gap) \
            or k2['high'] < k1['low'] * (1-min_gap):
        return True
    else:
        return False


def make_standard_seq(bi_seq):
    """计算标准特征序列

    :param bi_seq: list of dict
        笔标记序列
    :return: list of dict
        标准特征序列
    """
    if bi_seq[0]['fx_mark'] == 'd':
        direction = "up"
    elif bi_seq[0]['fx_mark'] == 'g':
        direction = "down"
    else:
        raise ValueError

    raw_seq = [{"start_dt": bi_seq[i]['dt'], "end_dt": bi_seq[i+1]['dt'],
                'high': max(bi_seq[i]['bi'], bi_seq[i + 1]['bi']),
                'low': min(bi_seq[i]['bi'], bi_seq[i + 1]['bi'])}
               for i in range(1, len(bi_seq), 2) if i <= len(bi_seq) - 2]

    seq = []
    for row in raw_seq:
        if not seq:
            seq.append(row)
            continue
        last = seq[-1]
        cur_h, cur_l = row['high'], row['low']
        last_h, last_l = last['high'], last['low']

        # 左包含 or 右包含
        if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
            seq.pop(-1)
            # 有包含关系，按方向分别处理
            if direction == "up":
                last_h = max(last_h, cur_h)
                last_l = max(last_l, cur_l)
            elif direction == "down":
                last_h = min(last_h, cur_h)
                last_l = min(last_l, cur_l)
            else:
                raise ValueError
            seq.append({"start_dt": last['start_dt'], "end_dt": row['end_dt'], "high": last_h, "low": last_l})
        else:
            seq.append(row)
    return seq


def is_valid_xd(bi_seq1, bi_seq2, bi_seq3):
    """判断线段标记是否有效（第二个线段标记）

    :param bi_seq1: list of dict
        第一个线段标记到第二个线段标记之间的笔序列
    :param bi_seq2:
        第二个线段标记到第三个线段标记之间的笔序列
    :param bi_seq3:
        第三个线段标记之后的笔序列
    :return:
    """
    assert bi_seq2[0]['dt'] == bi_seq1[-1]['dt'] and bi_seq3[0]['dt'] == bi_seq2[-1]['dt']

    standard_bi_seq1 = make_standard_seq(bi_seq1)
    if len(standard_bi_seq1) == 0 or len(bi_seq2) < 4:
        return False

    # 第一种情况（向下线段）
    # if bi_seq2[0]['fx_mark'] == 'd' and bi_seq2[1]['bi'] >= standard_bi_seq1[-1]['low']:
    if bi_seq2[0]['fx_mark'] == 'd' and bi_seq2[1]['bi'] >= min([x['low'] for x in standard_bi_seq1]):
        if bi_seq2[-1]['bi'] < bi_seq2[1]['bi']:
            return False

    # 第一种情况（向上线段）
    # if bi_seq2[0]['fx_mark'] == 'g' and bi_seq2[1]['bi'] <= standard_bi_seq1[-1]['high']:
    if bi_seq2[0]['fx_mark'] == 'g' and bi_seq2[1]['bi'] <= max([x['high'] for x in standard_bi_seq1]):
        if bi_seq2[-1]['bi'] > bi_seq2[1]['bi']:
            return False

    # 第二种情况（向下线段）
    # if bi_seq2[0]['fx_mark'] == 'd' and bi_seq2[1]['bi'] < standard_bi_seq1[-1]['low']:
    if bi_seq2[0]['fx_mark'] == 'd' and bi_seq2[1]['bi'] < min([x['low'] for x in standard_bi_seq1]):
        bi_seq2.extend(bi_seq3[1:])
        standard_bi_seq2 = make_standard_seq(bi_seq2)
        if len(standard_bi_seq2) < 3:
            return False

        standard_bi_seq2_g = []
        for i in range(1, len(standard_bi_seq2) - 1):
            bi1, bi2, bi3 = standard_bi_seq2[i-1: i+2]
            if bi1['high'] < bi2['high'] > bi3['high']:
                standard_bi_seq2_g.append(bi2)

                # 特征序列顶分型完全在底分型区间，返回 False
                if min(bi1['low'], bi2['low'], bi3['low']) < bi_seq2[0]['bi']:
                    return False

        if len(standard_bi_seq2_g) == 0:
            return False

    # 第二种情况（向上线段）
    # if bi_seq2[0]['fx_mark'] == 'g' and bi_seq2[1]['bi'] > standard_bi_seq1[-1]['high']:
    if bi_seq2[0]['fx_mark'] == 'g' and bi_seq2[1]['bi'] > max([x['high'] for x in standard_bi_seq1]):
        bi_seq2.extend(bi_seq3[1:])
        standard_bi_seq2 = make_standard_seq(bi_seq2)
        if len(standard_bi_seq2) < 3:
            return False

        standard_bi_seq2_d = []
        for i in range(1, len(standard_bi_seq2) - 1):
            bi1, bi2, bi3 = standard_bi_seq2[i-1: i+2]
            if bi1['low'] > bi2['low'] < bi3['low']:
                standard_bi_seq2_d.append(bi2)

                # 特征序列的底分型在顶分型区间，返回 False
                if max(bi1['high'], bi2['high'], bi3['high']) > bi_seq2[0]['bi']:
                    return False

        if len(standard_bi_seq2_d) == 0:
            return False
    return True


def get_potential_xd(bi_points):
    """获取潜在线段标记点

    :param bi_points: list of dict
        笔标记点
    :return: list of dict
        潜在线段标记点
    """
    xd_p = []
    bi_d = [x for x in bi_points if x['fx_mark'] == 'd']
    bi_g = [x for x in bi_points if x['fx_mark'] == 'g']
    for i in range(1, len(bi_d) - 1):
        d1, d2, d3 = bi_d[i - 1: i + 2]
        if d1['bi'] > d2['bi'] < d3['bi']:
            xd_p.append(d2)
    for j in range(1, len(bi_g) - 1):
        g1, g2, g3 = bi_g[j - 1: j + 2]
        if g1['bi'] < g2['bi'] > g3['bi']:
            xd_p.append(g2)

    xd_p = sorted(xd_p, key=lambda x: x['dt'], reverse=False)
    return xd_p


class KlineAnalyze:
    def __init__(self, kline, name="本级别", bi_mode="old", max_raw_len=10000, ma_params=(5, 20, 120), verbose=False):
        """

        :param kline: list or pd.DataFrame
        :param name: str
        :param bi_mode: str
            new 新笔；old 老笔；默认值为 old
        :param max_raw_len: int
            原始K线序列的最大长度
        :param ma_params: tuple of int
            均线系统参数
        :param verbose: bool
        """
        self.name = name
        self.verbose = verbose
        self.bi_mode = bi_mode
        self.max_raw_len = max_raw_len
        self.ma_params = ma_params
        self.kline_raw = []  # 原始K线序列
        self.kline_new = []  # 去除包含关系的K线序列

        # 辅助技术指标
        self.ma = []
        self.macd = []

        # 分型、笔、线段
        self.fx_list = []
        self.bi_list = []
        self.xd_list = []

        # 根据输入K线初始化
        if isinstance(kline, pd.DataFrame):
            columns = kline.columns.to_list()
            self.kline_raw = [{k: v for k, v in zip(columns, row)} for row in kline.values]
        else:
            self.kline_raw = kline

        self.kline_raw = self.kline_raw[-self.max_raw_len:]
        self.symbol = self.kline_raw[0]['symbol']
        self.start_dt = self.kline_raw[0]['dt']
        self.end_dt = self.kline_raw[-1]['dt']
        self.latest_price = self.kline_raw[-1]['close']

        self._update_ta()
        self._update_kline_new()
        self._update_fx_list()
        self._update_bi_list()
        self._update_xd_list()

    def _update_ta(self):
        """更新辅助技术指标"""
        if not self.ma:
            ma_temp = dict()
            close_ = np.array([x["close"] for x in self.kline_raw], dtype=np.double)
            for p in self.ma_params:
                ma_temp['ma%i' % p] = ta.SMA(close_, p)

            for i in range(len(self.kline_raw)):
                ma_ = {'ma%i' % p: ma_temp['ma%i' % p][i] for p in self.ma_params}
                ma_.update({"dt": self.kline_raw[i]['dt']})
                self.ma.append(ma_)
        else:
            ma_ = {'ma%i' % p: sum([x['close'] for x in self.kline_raw[-p:]]) / p
                   for p in self.ma_params}
            ma_.update({"dt": self.kline_raw[-1]['dt']})
            if self.verbose:
                print("ma new: %s" % str(ma_))

            if self.kline_raw[-2]['dt'] == self.ma[-1]['dt']:
                self.ma.append(ma_)
            else:
                self.ma[-1] = ma_

        assert self.ma[-2]['dt'] == self.kline_raw[-2]['dt']

        if not self.macd:
            close_ = np.array([x["close"] for x in self.kline_raw], dtype=np.double)
            # m1 is diff; m2 is dea; m3 is macd
            m1, m2, m3 = ta.MACD(close_, fastperiod=12, slowperiod=26, signalperiod=9)
            for i in range(len(self.kline_raw)):
                self.macd.append({
                    "dt": self.kline_raw[i]['dt'],
                    "diff": m1[i],
                    "dea": m2[i],
                    "macd": m3[i]
                })
        else:
            close_ = np.array([x["close"] for x in self.kline_raw[-200:]], dtype=np.double)
            # m1 is diff; m2 is dea; m3 is macd
            m1, m2, m3 = ta.MACD(close_, fastperiod=12, slowperiod=26, signalperiod=9)
            macd_ = {
                "dt": self.kline_raw[-1]['dt'],
                "diff": m1[-1],
                "dea": m2[-1],
                "macd": m3[-1]
            }
            if self.verbose:
                print("macd new: %s" % str(macd_))

            if self.kline_raw[-2]['dt'] == self.macd[-1]['dt']:
                self.macd.append(macd_)
            else:
                self.macd[-1] = macd_

        assert self.macd[-2]['dt'] == self.kline_raw[-2]['dt']

    def _update_kline_new(self):
        """更新去除包含关系的K线序列"""
        if len(self.kline_new) == 0:
            for x in self.kline_raw[:4]:
                self.kline_new.append(dict(x))

        # 新K线只会对最后一个去除包含关系K线的结果产生影响
        self.kline_new = self.kline_new[:-2]
        if len(self.kline_new) <= 4:
            right_k = [x for x in self.kline_raw if x['dt'] > self.kline_new[-1]['dt']]
        else:
            right_k = [x for x in self.kline_raw[-100:] if x['dt'] > self.kline_new[-1]['dt']]

        if len(right_k) == 0:
            return

        for k in right_k:
            k = dict(k)
            last_kn = self.kline_new[-1]
            if self.kline_new[-1]['high'] > self.kline_new[-2]['high']:
                direction = "up"
            else:
                direction = "down"

            # 判断是否存在包含关系
            cur_h, cur_l = k['high'], k['low']
            last_h, last_l = last_kn['high'], last_kn['low']
            if (cur_h <= last_h and cur_l >= last_l) or (cur_h >= last_h and cur_l <= last_l):
                self.kline_new.pop(-1)
                # 有包含关系，按方向分别处理
                if direction == "up":
                    last_h = max(last_h, cur_h)
                    last_l = max(last_l, cur_l)
                elif direction == "down":
                    last_h = min(last_h, cur_h)
                    last_l = min(last_l, cur_l)
                else:
                    raise ValueError

                k.update({"high": last_h, "low": last_l})
                # 保留红绿不变
                if k['open'] >= k['close']:
                    k.update({"open": last_h, "close": last_l})
                else:
                    k.update({"open": last_l, "close": last_h})
            self.kline_new.append(k)

    def _update_fx_list(self):
        """更新分型序列"""
        if len(self.kline_new) < 3:
            return

        self.fx_list = self.fx_list[:-1]
        if len(self.fx_list) == 0:
            kn = self.kline_new
        else:
            kn = [x for x in self.kline_new[-100:] if x['dt'] >= self.fx_list[-1]['dt']]

        i = 1
        while i <= len(kn) - 2:
            k1, k2, k3 = kn[i - 1: i + 2]
            fx_elements = [k1, k2, k3]
            if has_gap(k1, k2):
                fx_elements.pop(0)

            if has_gap(k2, k3):
                fx_elements.pop(-1)

            if k1['high'] < k2['high'] > k3['high']:
                if self.verbose:
                    print("顶分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "g",
                    "fx": k2['high'],
                    "start_dt": k1['dt'],
                    "end_dt": k3['dt'],
                    "fx_high": k2['high'],
                    "fx_low": min([x['low'] for x in fx_elements]),
                }
                self.fx_list.append(fx)

            elif k1['low'] > k2['low'] < k3['low']:
                if self.verbose:
                    print("底分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
                fx = {
                    "dt": k2['dt'],
                    "fx_mark": "d",
                    "fx": k2['low'],
                    "start_dt": k1['dt'],
                    "end_dt": k3['dt'],
                    "fx_high": max([x['high'] for x in fx_elements]),
                    "fx_low": k2['low'],
                }
                self.fx_list.append(fx)

            else:
                if self.verbose:
                    print("无分型：{} - {} - {}".format(k1['dt'], k2['dt'], k3['dt']))
            i += 1

    def _update_bi_list(self):
        """更新笔序列"""
        if len(self.fx_list) < 2:
            return

        self.bi_list = self.bi_list[:-2]
        if len(self.bi_list) == 0:
            for fx in self.fx_list[:2]:
                bi = dict(fx)
                bi['bi'] = bi.pop('fx')
                self.bi_list.append(bi)

        if len(self.bi_list) <= 2:
            right_fx = [x for x in self.fx_list if x['dt'] > self.bi_list[-1]['dt']]
            if self.bi_mode == "old":
                right_kn = [x for x in self.kline_new if x['dt'] >= self.bi_list[-1]['dt']]
            elif self.bi_mode == 'new':
                right_kn = [x for x in self.kline_raw if x['dt'] >= self.bi_list[-1]['dt']]
            else:
                raise ValueError
        else:
            right_fx = [x for x in self.fx_list[-50:] if x['dt'] > self.bi_list[-1]['dt']]
            if self.bi_mode == "old":
                right_kn = [x for x in self.kline_new[-300:] if x['dt'] >= self.bi_list[-1]['dt']]
            elif self.bi_mode == 'new':
                right_kn = [x for x in self.kline_raw[-300:] if x['dt'] >= self.bi_list[-1]['dt']]
            else:
                raise ValueError

        for fx in right_fx:
            last_bi = self.bi_list[-1]
            bi = dict(fx)
            bi['bi'] = bi.pop('fx')
            if last_bi['fx_mark'] == fx['fx_mark']:
                if (last_bi['fx_mark'] == 'g' and last_bi['bi'] < bi['bi']) \
                        or (last_bi['fx_mark'] == 'd' and last_bi['bi'] > bi['bi']):
                    if self.verbose:
                        print("笔标记移动：from {} to {}".format(self.bi_list[-1], bi))
                    self.bi_list[-1] = bi
            else:
                kn_inside = [x for x in right_kn if last_bi['end_dt'] < x['dt'] < bi['start_dt']]
                if len(kn_inside) <= 0:
                    continue

                # 确保相邻两个顶底之间不存在包含关系
                if (last_bi['fx_mark'] == 'g' and bi['fx_low'] < last_bi['fx_low']
                    and bi['fx_high'] < last_bi['fx_high']) or \
                        (last_bi['fx_mark'] == 'd' and bi['fx_high'] > last_bi['fx_high']
                         and bi['fx_low'] > last_bi['fx_low']):
                    if self.verbose:
                        print("新增笔标记：{}".format(bi))
                    self.bi_list.append(bi)

        if (self.bi_list[-1]['fx_mark'] == 'd' and self.kline_new[-1]['low'] < self.bi_list[-1]['bi']) \
                or (self.bi_list[-1]['fx_mark'] == 'g' and self.kline_new[-1]['high'] > self.bi_list[-1]['bi']):
            if self.verbose:
                print("最后一个笔标记无效，{}".format(self.bi_list[-1]))
            self.bi_list.pop(-1)

    def _update_xd_list_v1(self):
        """更新线段序列"""
        if len(self.bi_list) < 4:
            return

        self.xd_list = self.xd_list[:-2]
        if len(self.xd_list) == 0:
            for i in range(3):
                xd = dict(self.bi_list[i])
                xd['xd'] = xd.pop('bi')
                self.xd_list.append(xd)

        if len(self.xd_list) <= 3:
            right_bi = [x for x in self.bi_list if x['dt'] >= self.xd_list[-1]['dt']]
        else:
            right_bi = [x for x in self.bi_list[-200:] if x['dt'] >= self.xd_list[-1]['dt']]

        xd_p = get_potential_xd(right_bi)
        for xp in xd_p:
            xd = dict(xp)
            xd['xd'] = xd.pop('bi')
            last_xd = self.xd_list[-1]
            if last_xd['fx_mark'] == xd['fx_mark']:
                if (last_xd['fx_mark'] == 'd' and last_xd['xd'] > xd['xd']) \
                        or (last_xd['fx_mark'] == 'g' and last_xd['xd'] < xd['xd']):
                    if self.verbose:
                        print("更新线段标记：from {} to {}".format(last_xd, xd))
                    self.xd_list[-1] = xd
            else:
                if (last_xd['fx_mark'] == 'd' and last_xd['xd'] > xd['xd']) \
                        or (last_xd['fx_mark'] == 'g' and last_xd['xd'] < xd['xd']):
                    continue

                bi_inside = [x for x in right_bi if last_xd['dt'] <= x['dt'] <= xd['dt']]
                if len(bi_inside) < 4:
                    if self.verbose:
                        print("{} - {} 之间笔标记数量少于4，跳过".format(last_xd['dt'], xd['dt']))
                    continue
                else:
                    self.xd_list.append(xd)

    def _xd_after_process(self):
        """线段标记后处理，使用标准特征序列判断线段标记是否成立"""
        if not len(self.xd_list) > 4:
            return

        keep_xd_index = []
        for i in range(1, len(self.xd_list)-2):
            xd1, xd2, xd3, xd4 = self.xd_list[i-1: i+3]
            bi_seq1 = [x for x in self.bi_list if xd2['dt'] >= x['dt'] >= xd1['dt']]
            bi_seq2 = [x for x in self.bi_list if xd3['dt'] >= x['dt'] >= xd2['dt']]
            bi_seq3 = [x for x in self.bi_list if xd4['dt'] >= x['dt'] >= xd3['dt']]
            if len(bi_seq1) == 0 or len(bi_seq2) == 0 or len(bi_seq3) == 0:
                continue

            if is_valid_xd(bi_seq1, bi_seq2, bi_seq3):
                keep_xd_index.append(i)

        # 处理最近一个确定的线段标记
        bi_seq1 = [x for x in self.bi_list if self.xd_list[-2]['dt'] >= x['dt'] >= self.xd_list[-3]['dt']]
        bi_seq2 = [x for x in self.bi_list if self.xd_list[-1]['dt'] >= x['dt'] >= self.xd_list[-2]['dt']]
        bi_seq3 = [x for x in self.bi_list if x['dt'] >= self.xd_list[-1]['dt']]
        if not (len(bi_seq1) == 0 or len(bi_seq2) == 0 or len(bi_seq3) == 0):
            if is_valid_xd(bi_seq1, bi_seq2, bi_seq3):
                keep_xd_index.append(len(self.xd_list) - 2)

        # 处理最近一个未确定的线段标记
        if len(bi_seq3) >= 4:
            keep_xd_index.append(len(self.xd_list) - 1)

        new_xd_list = []
        for j in keep_xd_index:
            if not new_xd_list:
                new_xd_list.append(self.xd_list[j])
            else:
                if new_xd_list[-1]['fx_mark'] == self.xd_list[j]['fx_mark']:
                    if (new_xd_list[-1]['fx_mark'] == 'd' and new_xd_list[-1]['xd'] > self.xd_list[j]['xd']) \
                            or (new_xd_list[-1]['fx_mark'] == 'g' and new_xd_list[-1]['xd'] < self.xd_list[j]['xd']):
                        new_xd_list[-1] = self.xd_list[j]
                else:
                    new_xd_list.append(self.xd_list[j])
        self.xd_list = new_xd_list

        # 针对最近一个线段标记处理
        if (self.xd_list[-1]['fx_mark'] == 'd' and self.bi_list[-1]['bi'] < self.xd_list[-1]['xd']) \
                or (self.xd_list[-1]['fx_mark'] == 'g' and self.bi_list[-1]['bi'] > self.xd_list[-1]['xd']):
            self.xd_list.pop(-1)

    def _update_xd_list(self):
        self._update_xd_list_v1()
        self._xd_after_process()

    def update(self, k):
        """更新分析结果

        :param k: dict
            单根K线对象，样例如下
            {'symbol': '000001.SH',
             'dt': Timestamp('2020-07-16 15:00:00'),
             'open': 3356.11,
             'close': 3210.1,
             'high': 3373.53,
             'low': 3209.76,
             'vol': 486366915.0}
        """
        if self.verbose:
            print("=" * 100)
            print("输入新K线：{}".format(k))
        if not self.kline_raw or k['open'] != self.kline_raw[-1]['open']:
            self.kline_raw.append(k)
        else:
            if self.verbose:
                print("输入K线处于未完成状态，更新：replace {} with {}".format(self.kline_raw[-1], k))
            self.kline_raw[-1] = k

        self._update_ta()
        self._update_kline_new()
        self._update_fx_list()
        self._update_bi_list()
        self._update_xd_list()

        self.end_dt = self.kline_raw[-1]['dt']
        self.latest_price = self.kline_raw[-1]['close']

        # 根据最大原始K线序列长度限制分析结果长度
        if len(self.kline_raw) > self.max_raw_len:
            self.kline_raw = self.kline_raw[-self.max_raw_len:]
            self.kline_new = self.kline_new[-self.max_raw_len:]
            self.ma = self.ma[-self.max_raw_len:]
            self.macd = self.macd[-self.max_raw_len:]
            last_dt = self.kline_new[0]['dt']
            self.fx_list = [x for x in self.fx_list if x['dt'] > last_dt]
            self.bi_list = [x for x in self.bi_list if x['dt'] > last_dt]
            self.xd_list = [x for x in self.xd_list if x['dt'] > last_dt]

            # self.fx_list = self.fx_list[-(self.max_raw_len // 2):]
            # self.bi_list = self.bi_list[-(self.max_raw_len // 4):]
            # self.xd_list = self.xd_list[-(self.max_raw_len // 8):]

        if self.verbose:
            print("更新结束\n\n")

    def to_df(self, ma_params=(5, 20), use_macd=False, max_count=1000, mode="raw"):
        """整理成 df 输出

        :param ma_params: tuple of int
            均线系统参数
        :param use_macd: bool
        :param max_count: int
        :param mode: str
            使用K线类型， raw = 原始K线，new = 去除包含关系的K线
        :return: pd.DataFrame
        """
        if mode == "raw":
            bars = self.kline_raw[-max_count:]
        elif mode == "new":
            bars = self.kline_raw[-max_count:]
        else:
            raise ValueError

        fx_list = {x["dt"]: {"fx_mark": x["fx_mark"], "fx": x['fx']} for x in self.fx_list[-(max_count // 2):]}
        bi_list = {x["dt"]: {"fx_mark": x["fx_mark"], "bi": x['bi']} for x in self.bi_list[-(max_count // 4):]}
        xd_list = {x["dt"]: {"fx_mark": x["fx_mark"], "xd": x['xd']} for x in self.xd_list[-(max_count // 8):]}
        results = []
        for k in bars:
            k['fx_mark'], k['fx'], k['bi'], k['xd'] = "o", None, None, None
            fx_ = fx_list.get(k['dt'], None)
            bi_ = bi_list.get(k['dt'], None)
            xd_ = xd_list.get(k['dt'], None)
            if fx_:
                k['fx_mark'] = fx_["fx_mark"]
                k['fx'] = fx_["fx"]

            if bi_:
                k['bi'] = bi_["bi"]

            if xd_:
                k['xd'] = xd_["xd"]

            results.append(k)
        df = pd.DataFrame(results)
        for p in ma_params:
            df.loc[:, "ma{}".format(p)] = ta.SMA(df.close.values, p)
        if use_macd:
            diff, dea, macd = ta.MACD(df.close.values)
            df.loc[:, "diff"] = diff
            df.loc[:, "dea"] = diff
            df.loc[:, "macd"] = diff
        return df

    def to_image(self, file_image, mav=(5, 20, 120, 250), max_k_count=1000, dpi=50):
        """保存成图片

        :param file_image: str
            图片名称，支持 jpg/png/svg 格式，注意后缀
        :param mav: tuple of int
            均线系统参数
        :param max_k_count: int
            设定最大K线数量，这个值越大，生成的图片越长
        :param dpi: int
            图片分辨率
        :return:
        """
        plot_ka(self, file_image=file_image, mav=mav, max_k_count=max_k_count, dpi=dpi)

    def is_bei_chi(self, zs1, zs2, mode="bi", adjust=0.9, last_index: int = None):
        """判断 zs1 对 zs2 是否有背驰

        注意：力度的比较，并没有要求两段走势方向一致；但是如果两段走势之间存在包含关系，这样的力度比较是没有意义的。

        :param zs1: dict
            用于比较的走势，通常是最近的走势，示例如下：
            zs1 = {"start_dt": "2020-02-20 11:30:00", "end_dt": "2020-02-20 14:30:00", "direction": "up"}
        :param zs2: dict
            被比较的走势，通常是较前的走势，示例如下：
            zs2 = {"start_dt": "2020-02-21 11:30:00", "end_dt": "2020-02-21 14:30:00", "direction": "down"}
        :param mode: str
            default `bi`, optional value [`xd`, `bi`]
            xd  判断两个线段之间是否存在背驰
            bi  判断两笔之间是否存在背驰
        :param adjust: float
            调整 zs2 的力度，建议设置范围在 0.6 ~ 1.0 之间，默认设置为 0.9；
            其作用是确保 zs1 相比于 zs2 的力度足够小。
        :param last_index: int
            在比较最后一个走势的时候，可以设置这个参数来提升速度，相当于只对 last_index 后面的K线进行力度比较
        :return: bool
        """
        assert zs1["start_dt"] > zs2["end_dt"], "zs1 必须是最近的走势，用于比较；zs2 必须是较前的走势，被比较。"
        assert zs1["start_dt"] < zs1["end_dt"], "走势的时间区间定义错误，必须满足 start_dt < end_dt"
        assert zs2["start_dt"] < zs2["end_dt"], "走势的时间区间定义错误，必须满足 start_dt < end_dt"

        min_dt = min(zs1["start_dt"], zs2["start_dt"])
        max_dt = max(zs1["end_dt"], zs2["end_dt"])
        if last_index:
            macd = self.macd[-last_index:]
        else:
            macd = self.macd
        macd_ = [x for x in macd if x['dt'] >= min_dt]
        macd_ = [x for x in macd_ if max_dt >= x['dt']]
        k1 = [x for x in macd_ if zs1["end_dt"] >= x['dt'] >= zs1["start_dt"]]
        k2 = [x for x in macd_ if zs2["end_dt"] >= x['dt'] >= zs2["start_dt"]]

        bc = False
        if mode == 'bi':
            macd_sum1 = sum([abs(x['macd']) for x in k1])
            macd_sum2 = sum([abs(x['macd']) for x in k2])
            # print("bi: ", macd_sum1, macd_sum2)
            if macd_sum1 < macd_sum2 * adjust:
                bc = True

        elif mode == 'xd':
            assert zs1['direction'] in ['down', 'up'], "走势的 direction 定义错误，可取值为 up 或 down"
            assert zs2['direction'] in ['down', 'up'], "走势的 direction 定义错误，可取值为 up 或 down"

            if zs1['direction'] == "down":
                macd_sum1 = sum([abs(x['macd']) for x in k1 if x['macd'] < 0])
            else:
                macd_sum1 = sum([abs(x['macd']) for x in k1 if x['macd'] > 0])

            if zs2['direction'] == "down":
                macd_sum2 = sum([abs(x['macd']) for x in k2 if x['macd'] < 0])
            else:
                macd_sum2 = sum([abs(x['macd']) for x in k2 if x['macd'] > 0])

            # print("xd: ", macd_sum1, macd_sum2)
            if macd_sum1 < macd_sum2 * adjust:
                bc = True

        else:
            raise ValueError("mode value error")

        return bc

    def get_sub_section(self, start_dt: datetime, end_dt: datetime, mode="bi", is_last=True):
        """获取子区间

        :param start_dt: datetime
            子区间开始时间
        :param end_dt: datetime
            子区间结束时间
        :param mode: str
            需要获取的子区间对象类型，可取值 ['kn', 'fx', 'bi', 'xd']
        :param is_last: bool
            是否是最近一段子区间
        :return: list of dict
        """
        if mode == "kn":
            if is_last:
                points = self.kline_new[-200:]
            else:
                points = self.kline_new
        elif mode == "fx":
            if is_last:
                points = self.fx_list[-100:]
            else:
                points = self.fx_list
        elif mode == "bi":
            if is_last:
                points = self.bi_list[-50:]
            else:
                points = self.bi_list
        elif mode == "xd":
            if is_last:
                points = self.xd_list[-30:]
            else:
                points = self.xd_list
        else:
            raise ValueError

        return [x for x in points if end_dt >= x['dt'] >= start_dt]

    def calculate_macd_power(self, start_dt: datetime, end_dt: datetime, mode='bi', direction="up"):
        """用 MACD 计算走势段（start_dt ~ end_dt）的力度

        :param start_dt: datetime
            走势开始时间
        :param end_dt: datetime
            走势结束时间
        :param mode: str
            分段走势类型，默认值为 bi，可选值 ['bi', 'xd']，分别表示笔分段走势和线段分段走势
        :param direction: str
            线段分段走势计算力度需要指明方向，可选值 ['up', 'down']
        :return: float
            走势力度
        """
        fd_macd = [x for x in self.macd if end_dt >= x['dt'] >= start_dt]

        if mode == 'bi':
            power = sum([abs(x['macd']) for x in fd_macd])
        elif mode == 'xd':
            if direction == 'up':
                power = sum([abs(x['macd']) for x in fd_macd if x['macd'] > 0])
            elif direction == 'down':
                power = sum([abs(x['macd']) for x in fd_macd if x['macd'] < 0])
            else:
                raise ValueError
        else:
            raise ValueError
        return power

    def calculate_vol_power(self, start_dt: datetime, end_dt: datetime):
        """用 VOL 计算走势段（start_dt ~ end_dt）的力度

        :param start_dt: datetime
            走势开始时间
        :param end_dt: datetime
            走势结束时间
        :return: float
            走势力度
        """
        fd_vol = [x for x in self.kline_raw if end_dt >= x['dt'] >= start_dt]
        power = sum([x['vol'] for x in fd_vol])
        return int(power)


class KlineGenerator:
    """K线生成器，仿实盘"""

    def __init__(self, max_count=5000, freqs=None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        self.max_count = max_count
        if freqs is None:
            self.freqs = ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        else:
            self.freqs = freqs
        self.m1 = []
        self.m5 = []
        self.m15 = []
        self.m30 = []
        self.m60 = []
        self.D = []
        self.W = []
        self.end_dt = None
        self.symbol = None

    def __repr__(self):
        return "<KlineGenerator for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    def update(self, k):
        """输入1分钟最新K线，更新其他级别K线

        :param k: dict
            {'symbol': '000001.XSHG',
             'dt': Timestamp('2020-07-16 14:51:00'),  # 必须是K线结束时间
             'open': 3216.8,
             'close': 3216.63,
             'high': 3216.95,
             'low': 3216.2,
             'vol': '270429600'}
        """
        self.end_dt = k['dt']
        self.symbol = k['symbol']

        # 更新1分钟线
        if "1分钟" in self.freqs:
            if not self.m1:
                self.m1.append(k)
            else:
                if k['dt'] > self.m1[-1]['dt']:
                    self.m1.append(k)
                elif k['dt'] == self.m1[-1]['dt']:
                    self.m1[-1] = k
                else:
                    raise ValueError("1分钟新K线的时间必须大于等于最后一根K线的时间")
            self.m1 = self.m1[-self.max_count:]

        # 更新5分钟线
        if "5分钟" in self.freqs:
            if not self.m5:
                self.m5.append(k)
            last_m5 = self.m5[-1]
            if last_m5['dt'].minute % 5 == 0 and k['dt'].minute % 5 != 0:
                self.m5.append(k)
            else:
                new = dict(last_m5)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m5['high']),
                    "low": min(k['low'], last_m5['low']),
                    "vol": k['vol'] + last_m5['vol']
                })
                self.m5[-1] = new
            self.m5 = self.m5[-self.max_count:]

        # 更新15分钟线
        if "15分钟" in self.freqs:
            if not self.m15:
                self.m15.append(k)
            last_m15 = self.m15[-1]
            if last_m15['dt'].minute % 15 == 0 and k['dt'].minute % 15 != 0:
                self.m15.append(k)
            else:
                new = dict(last_m15)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m15['high']),
                    "low": min(k['low'], last_m15['low']),
                    "vol": k['vol'] + last_m15['vol']
                })
                self.m15[-1] = new
            self.m15 = self.m15[-self.max_count:]

        # 更新30分钟线
        if "30分钟" in self.freqs:
            if not self.m30:
                self.m30.append(k)
            last_m30 = self.m30[-1]
            if last_m30['dt'].minute % 30 == 0 and k['dt'].minute % 30 != 0:
                self.m30.append(k)
            else:
                new = dict(last_m30)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m30['high']),
                    "low": min(k['low'], last_m30['low']),
                    "vol": k['vol'] + last_m30['vol']
                })
                self.m30[-1] = new
            self.m30 = self.m30[-self.max_count:]

        # 更新60分钟线
        if "60分钟" in self.freqs:
            if not self.m60:
                self.m60.append(k)
            last_m60 = self.m60[-1]
            if last_m60['dt'].minute % 60 == 0 and k['dt'].minute % 60 != 0:
                self.m60.append(k)
            else:
                new = dict(last_m60)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m60['high']),
                    "low": min(k['low'], last_m60['low']),
                    "vol": k['vol'] + last_m60['vol']
                })
                self.m60[-1] = new
            self.m60 = self.m60[-self.max_count:]

        # 更新日线
        if "日线" in self.freqs:
            if not self.D:
                self.D.append(k)
            last_d = self.D[-1]
            if k['dt'].date() != last_d['dt'].date():
                self.D.append(k)
            else:
                new = dict(last_d)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_d['high']),
                    "low": min(k['low'], last_d['low']),
                    "vol": k['vol'] + last_d['vol']
                })
                self.D[-1] = new
            self.D = self.D[-self.max_count:]

        # 更新周线
        if "周线" in self.freqs:
            if not self.W:
                self.W.append(k)
            last_w = self.W[-1]
            if k['dt'].weekday() == 0 and k['dt'].weekday() != last_w['dt'].weekday():
                self.W.append(k)
            else:
                new = dict(last_w)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_w['high']),
                    "low": min(k['low'], last_w['low']),
                    "vol": k['vol'] + last_w['vol']
                })
                self.W[-1] = new
            self.W = self.W[-self.max_count:]

    def get_kline(self, freq, count):
        """获取单个级别的K线

        :param freq: str
            级别名称，可选值 1分钟；5分钟；15分钟；30分钟；60分钟；日线；周线
        :param count: int
            数量
        :return: list of dict
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15,
                     "30分钟": self.m30, "60分钟": self.m60, "日线": self.D, "周线": self.W}
        return [dict(x) for x in freqs_map[freq][-count:]]

    def get_klines(self, counts=None):
        """获取多个级别的K线

        :param counts: dict
            默认值 {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        :return: dict of list of dict
        """
        if counts is None:
            counts = {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        return {k: self.get_kline(k, v) for k, v in counts.items()}


def check_jing(fd1, fd2, fd3, fd4, fd5):
    """检查最近5个分段走势是否构成井

    井的定义：
        12345，五段，是构造井的基本形态，形成井的位置肯定是5，而5出井的
        前提条件是对于向上5至少比3和1其中之一高，向下反过来; 并且，234
        构成一个中枢。

        井只有两类，大井和小井（以向上为例）：
        大井对应的形式是：12345向上，5最高3次之1最低，力度上1大于3，3大于5；
        小井对应的形式是：
            1：12345向上，3最高5次之1最低，力度上5的力度比1小，注意这时候
               不需要再考虑5和3的关系了，因为5比3低，所以不需要考虑力度。
            2：12345向上，5最高3次之1最低，力度上1大于5，5大于3。

        小井的构造，关键是满足5一定至少大于1、3中的一个。
        注意有一种情况不归为井：就是12345向上，1的力度最小，5的力度次之，3的力度最大此类不算井，
        因为345后面必然还有走势在67的时候才能再判断，个中道理各位好好体会。


    fd 为 dict 对象，表示一段走势，可以是笔、线段，样例如下：

    fd = {
        "start_dt": "",
        "end_dt": "",
        "power": 0,         # 力度
        "direction": "up",
        "high": 0,
        "low": 0,
        "mode": "bi"
    }

    """
    assert fd1['direction'] == fd3['direction'] == fd5['direction']
    assert fd2['direction'] == fd4['direction']
    direction = fd1['direction']

    zs_g = min(fd2['high'], fd3['high'], fd4['high'])
    zs_d = max(fd2['low'], fd3['low'], fd4['low'])

    jing = "没有出井"
    if zs_d < zs_g:
        if direction == 'up' and fd5["high"] > min(fd3['high'], fd1['high']):

            # 大井对应的形式是：12345向上，5最高3次之1最低，力度上1大于3，3大于5
            if fd5["high"] > fd3['high'] > fd1['high'] and fd5['power'] < fd3['power'] < fd1['power']:
                jing = "向上大井"

            # 第一种小井：12345向上，3最高5次之1最低，力度上5的力度比1小
            if fd1['high'] < fd5['high'] < fd3['high'] and fd5['power'] < fd1['power']:
                jing = "向上小井"

            # 第二种小井：12345向上，5最高3次之1最低，力度上1大于5，5大于3
            if fd5["high"] > fd3['high'] > fd1['high'] and fd1['power'] > fd5['power'] > fd3['power']:
                jing = "向上小井"

        if direction == 'down' and fd5["low"] < max(fd3['low'], fd1['low']):

            # 大井对应的形式是：12345向下，5最低3次之1最高，力度上1大于3，3大于5；
            if fd5['low'] < fd3['low'] < fd1['low'] and fd5['power'] < fd3['power'] < fd1['power']:
                jing = "向下大井"

            # 第一种小井：12345向下，3最低5次之1最高，力度上5的力度比1小
            if fd1["low"] > fd5['low'] > fd3['low'] and fd5['power'] < fd1['power']:
                jing = "向下小井"

            # 第二种小井：12345向下，5最低3次之1最高，力度上1大于5，5大于3
            if fd3["low"] > fd5['low'] > fd1['low'] and fd1['power'] > fd5['power'] > fd3['power']:
                jing = "向下小井"

    return jing


def get_fx_signals(ka):
    """计算分型特征"""
    s = {
        "收于MA5上方": False,
        "收于MA5下方": False,
        "收于MA20上方": False,
        "收于MA20下方": False,
        "收于MA120上方": False,
        "收于MA120下方": False,
        "最后一个分型为顶": False,
        "最后一个分型为底": False,
        "顶分型后有效跌破MA5": False,
        "底分型后有效升破MA5": False,
        "最近三K线形态": None,
    }

    last_tri = ka.kline_new[-3:]
    if len(last_tri) == 3:
        if last_tri[-3]['high'] < last_tri[-2]['high'] > last_tri[-1]['high']:
            s["最近三K线形态"] = "g"
        elif last_tri[-3]['low'] > last_tri[-2]['low'] < last_tri[-1]['low']:
            s["最近三K线形态"] = "d"
        elif last_tri[-3]['low'] > last_tri[-2]['low'] > last_tri[-1]['low']:
            s["最近三K线形态"] = "down"
        elif last_tri[-3]['high'] < last_tri[-2]['high'] < last_tri[-1]['high']:
            s["最近三K线形态"] = "up"

    last_klines_ = [dict(x) for x in ka.kline_raw[-10:]]
    if len(last_klines_) != 10:
        return s

    last_ma_ = ka.ma[-10:]
    for i, x in enumerate(last_klines_):
        assert last_ma_[i]['dt'] == x['dt'], "{}：计算均线错误".format(ka.name)
        last_klines_[i].update(last_ma_[i])

    last_k = last_klines_[-1]
    if last_k['close'] >= last_k['ma5']:
        s["收于MA5上方"] = True
    else:
        s["收于MA5下方"] = True

    if last_k['close'] >= last_k['ma20']:
        s["收于MA20上方"] = True
    else:
        s["收于MA20下方"] = True

    if last_k['close'] >= last_k['ma120']:
        s["收于MA120上方"] = True
    else:
        s["收于MA120下方"] = True

    last_fx = ka.fx_list[-1]
    after_klines = [x for x in last_klines_ if x['dt'] >= last_fx['dt']]
    if last_fx['fx_mark'] == 'g':
        s["最后一个分型为顶"] = True
        # 顶分型有效跌破MA5的三种情况：1）分型右侧第一根K线收于MA5下方；2）连续5根K线最低价下穿MA5；3）连续3根K线收盘价收于MA5下方
        if after_klines[1]['close'] < after_klines[1]['ma5'] \
                or sum([1 for x in after_klines[-5:] if x['low'] < x['ma5']]) >= 5 \
                or sum([1 for x in after_klines[-3:] if x['close'] < x['ma5']]) >= 3:
            s['顶分型后有效跌破MA5'] = True

    if last_fx['fx_mark'] == 'd':
        s["最后一个分型为底"] = True
        # 底分型后有效升破MA5的三种情况：1）分型右侧第一根K线收于MA5上方；2）连续5根K线最高价上穿MA5；3）连续3根K线收盘价收于MA5上方
        if after_klines[1]['close'] > after_klines[1]['ma5'] \
                or sum([1 for x in after_klines[-5:] if x['high'] > x['ma5']]) >= 5 \
                or sum([1 for x in after_klines[-3:] if x['close'] > x['ma5']]) >= 3:
            s['底分型后有效升破MA5'] = True
    freq = ka.name
    return {freq + k: v for k, v in s.items()}


def get_bi_signals(ka):
    """计算笔信号"""
    s = {
        "最后一个未确认的笔标记为底": False,
        "最后一个未确认的笔标记为顶": False,
        "最后一个已确认的笔标记为底": False,
        "最后一个已确认的笔标记为顶": False,
        "向上笔走势延伸": False,
        "向上笔现顶分型": False,
        "向下笔走势延伸": False,
        "向下笔现底分型": False,

        "最后一个笔中枢上沿": 0,
        "最后一个笔中枢下沿": 0,
        "收于笔中枢上方且有三买": False,
        "收于笔中枢上方且无三买": False,
        "收于笔中枢下方且有三卖": False,
        "收于笔中枢下方且无三卖": False,

        '笔同级别分解买': False,
        '笔同级别分解卖': False,

        '类趋势顶背驰（笔）': False,
        '类趋势底背驰（笔）': False,
        '类盘整顶背驰（笔）': False,
        '类盘整底背驰（笔）': False,

        # '趋势顶背驰（笔）': False,
        # '趋势底背驰（笔）': False,
        # '盘整顶背驰（笔）': False,
        # '盘整底背驰（笔）': False,
    }

    # ------------------------------------------------------------------------------------------------------------------
    if len(ka.bi_list) > 2:
        assert ka.bi_list[-1]['fx_mark'] in ['d', 'g']
        if ka.bi_list[-1]['fx_mark'] == 'd':
            s["最后一个未确认的笔标记为底"] = True
        else:
            s["最后一个未确认的笔标记为顶"] = True

        assert ka.bi_list[-2]['fx_mark'] in ['d', 'g']
        if ka.bi_list[-2]['fx_mark'] == 'd':
            s["最后一个已确认的笔标记为底"] = True
        else:
            s["最后一个已确认的笔标记为顶"] = True

    # ------------------------------------------------------------------------------------------------------------------
    last_bi = ka.bi_list[-1]
    if last_bi['fx_mark'] == 'd' and ka.fx_list[-1]['fx_mark'] == 'd':
        s["向上笔走势延伸"] = True
    elif last_bi['fx_mark'] == 'd' and ka.fx_list[-1]['fx_mark'] == 'g':
        s["向上笔现顶分型"] = True
    elif last_bi['fx_mark'] == 'g' and ka.fx_list[-1]['fx_mark'] == 'g':
        s['向下笔走势延伸'] = True
    elif last_bi['fx_mark'] == 'g' and ka.fx_list[-1]['fx_mark'] == 'd':
        s['向下笔现底分型'] = True
    else:
        raise ValueError("笔状态识别错误，最后一个笔标记：%s，"
                         "最后一个分型标记%s" % (str(last_bi), str(ka.fx_list[-1])))

    # ------------------------------------------------------------------------------------------------------------------
    bis = ka.bi_list[-30:]
    if len(bis) >= 6:
        if bis[-1]['fx_mark'] == 'd' and bis[-1]['bi'] < bis[-3]['bi'] and bis[-2]['bi'] < bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] < bis[-5]['bi']:
                    s['类趋势底背驰（笔）'] = True
                else:
                    s['类盘整底背驰（笔）'] = True

        if bis[-1]['fx_mark'] == 'g' and bis[-1]['bi'] > bis[-3]['bi'] and bis[-2]['bi'] > bis[-4]['bi']:
            zs1 = {"start_dt": bis[-2]['dt'], "end_dt": bis[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": bis[-4]['dt'], "end_dt": bis[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="bi", adjust=0.9):
                # 类趋势
                if bis[-2]['bi'] > bis[-5]['bi']:
                    s['类趋势顶背驰（笔）'] = True
                else:
                    s['类盘整顶背驰（笔）'] = True

    # ------------------------------------------------------------------------------------------------------------------
    bi_zs = find_zs(bis)
    if bi_zs:
        last_bi_zs = bi_zs[-1]
        s["最后一个笔中枢上沿"] = last_bi_zs['ZG']
        s["最后一个笔中枢下沿"] = last_bi_zs['ZD']

        last_k = ka.kline_new[-1]
        if last_k['close'] > last_bi_zs['ZG']:
            if last_bi_zs.get("third_buy", 0):
                s["收于笔中枢上方且有三买"] = True
            else:
                s["收于笔中枢上方且无三买"] = True

        if last_k['close'] < last_bi_zs['ZD']:
            if last_bi_zs.get("third_sell", 0):
                s["收于笔中枢下方且有三卖"] = True
            else:
                s["收于笔中枢下方且无三卖"] = True

    # ------------------------------------------------------------------------------------------------------------------
    if len(bis) >= 6:
        if bis[-1]['fx_mark'] == 'd' and bis[-2]['bi'] > bis[-5]['bi']:
            if bis[-1]['bi'] > bis[-3]['bi'] or s['类盘整底背驰（笔）']:
                s['笔同级别分解买'] = True

        if bis[-1]['fx_mark'] == 'g' and bis[-2]['bi'] < bis[-5]['bi']:
            if bis[-1]['bi'] < bis[-3]['bi'] or s['类盘整顶背驰（笔）']:
                s['笔同级别分解卖'] = True

    freq = ka.name
    return {freq + k: v for k, v in s.items()}


def get_xd_signals(ka, use_zs=False):
    """计算线段方向特征"""
    s = {
        "最后一个未确认的线段标记为底": False,
        "最后一个未确认的线段标记为顶": False,
        "最后一个已确认的线段标记为底": False,
        "最后一个已确认的线段标记为顶": False,

        "最后一个线段内部笔标记数量": 0,
        "最近上一线段内部笔标记数量": 0,

        '类趋势顶背驰（段）': False,
        '类趋势底背驰（段）': False,
        '类盘整顶背驰（段）': False,
        '类盘整底背驰（段）': False,

        "同级别分解买": False,
        "同级别分解卖": False,

        # '趋势顶背驰（段）': False,
        # '趋势底背驰（段）': False,
        # '盘整顶背驰（段）': False,
        # '盘整底背驰（段）': False,
        # "最后一个中枢上沿": 0,
        # "最后一个中枢下沿": 0,
    }

    # ------------------------------------------------------------------------------------------------------------------
    assert ka.xd_list[-1]['fx_mark'] in ['g', 'd']
    if ka.xd_list[-1]['fx_mark'] == 'd':
        s["最后一个未确认的线段标记为底"] = True
    else:
        s["最后一个未确认的线段标记为顶"] = True

    assert ka.xd_list[-2]['fx_mark'] in ['g', 'd']
    if ka.xd_list[-2]['fx_mark'] == 'd':
        s["最后一个已确认的线段标记为底"] = True
    else:
        s["最后一个已确认的线段标记为顶"] = True

    # ------------------------------------------------------------------------------------------------------------------
    bi_after = [x for x in ka.bi_list[-60:] if x['dt'] >= ka.xd_list[-1]['dt']]
    s["最后一个线段内部笔标记数量"] = len(bi_after)
    s["最近上一线段内部笔标记数量"] = len([x for x in ka.bi_list[-100:]
                              if ka.xd_list[-2]['dt'] <= x['dt'] <= ka.xd_list[-1]['dt']])

    # ------------------------------------------------------------------------------------------------------------------
    xds = ka.xd_list[-50:]
    if len(xds) >= 6:
        if xds[-1]['fx_mark'] == 'd' and xds[-1]['xd'] < xds[-3]['xd'] and xds[-2]['xd'] < xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "down"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "down"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] < xds[-5]['xd']:
                    s['类趋势底背驰（段）'] = True
                else:
                    s['类盘整底背驰（段）'] = True

        if xds[-1]['fx_mark'] == 'g' and xds[-1]['xd'] > xds[-3]['xd'] and xds[-2]['xd'] > xds[-4]['xd']:
            zs1 = {"start_dt": xds[-2]['dt'], "end_dt": xds[-1]['dt'], "direction": "up"}
            zs2 = {"start_dt": xds[-4]['dt'], "end_dt": xds[-3]['dt'], "direction": "up"}
            if ka.is_bei_chi(zs1, zs2, mode="xd", adjust=0.9):
                # 类趋势
                if xds[-2]['xd'] > xds[-5]['xd']:
                    s['类趋势顶背驰（段）'] = True
                else:
                    s['类盘整顶背驰（段）'] = True

    # ------------------------------------------------------------------------------------------------------------------
    last_xd_inside = [x for x in ka.bi_list[-60:] if x['dt'] >= xds[-1]['dt']]
    if len(xds) >= 6 and len(last_xd_inside) >= 6:
        if xds[-1]['fx_mark'] == 'g' and xds[-2]['xd'] < xds[-5]['xd']:
            if xds[-1]['xd'] < xds[-3]['xd'] or s['类盘整底背驰（段）']:
                s['同级别分解买'] = True

        if xds[-1]['fx_mark'] == 'd' and xds[-2]['xd'] > xds[-5]['xd']:
            if xds[-1]['xd'] > xds[-3]['xd'] or s['类盘整顶背驰（段）']:
                s['同级别分解卖'] = True

    # ------------------------------------------------------------------------------------------------------------------
    freq = ka.name
    return {freq + k: v for k, v in s.items()}


class Signals:
    def __init__(self, klines):
        """
        :param klines: dict
            K线数据
        """
        self.klines = klines
        self.kas = {k: KlineAnalyze(self.klines[k], name=k, min_bi_k=5,
                                    ma_params=(5, 20, 120),
                                    max_raw_len=5000, verbose=False)
                    for k in self.klines.keys()}
        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price

    def __repr__(self):
        return "<Signals of {}>".format(self.symbol)

    def signals(self):
        """计算交易决策需要的状态信息"""
        s = {"symbol": self.symbol}

        for k in self.kas.keys():
            if k in ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_fx_signals(self.kas[k]))

            if k in ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_bi_signals(self.kas[k]))

            if k in ['日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']:
                s.update(get_xd_signals(self.kas[k]))
        return s

    def update_kas(self, klines_one):
        for freq, klines_ in klines_one.items():
            k = klines_[-1]
            self.kas[freq].update(k)

        self.symbol = self.kas["1分钟"].symbol
        self.end_dt = self.kas["1分钟"].end_dt
        self.latest_price = self.kas["1分钟"].latest_price


