import yaml
import pandas as pd

dt_values = [5, 10, 20, 40, 80]
DV_tol = 10000
results_files = ['results_10obj/10obj_dt%d_results.yml' % dt for dt in dt_values]



def format_seq(tup):
    s = ''
    for t_idx, t in enumerate(tup):
        if t_idx > 0:
            s+=' -> '
        s+=str(t).ljust(3)
    return s
        
def process(mode='dv'):
    dfs = list()
    for idx in range(len(dt_values)):
        sequences = list()
        DV_values = list()
        with open(results_files[idx]) as f:
            lines = f.readlines()

        minDV = float(lines[0].split(':')[1].strip(' '))
        for l_idx, l in enumerate(lines):
            tup_string, dvstring = l.split(':')
            dv = float(dvstring.strip(' '))
            if dv <= minDV+DV_tol:
                sequences.append(format_seq(tuple(int(x) for x in tup_string.strip(' ')[1:-1].split(','))))
                if mode == 'dv': DV_values.append(dv)
                if mode == 'dv_int': DV_values.append(int(dv))
                if mode == 'order': DV_values.append(l_idx+1)
        df = pd.DataFrame(data = {dt_values[idx]: DV_values}, index=sequences)
        dfs.append(df)

    joined_df = pd.concat(dfs, axis=1)
    joined_df = joined_df.sort_values(by=dt_values[0])
    return joined_df

process(mode='dv').to_csv('results_10obj/10obj_dv.csv')
process(mode='dv_int').to_csv('results_10obj/10obj_dvint.csv')
process(mode='order').to_csv('results_10obj/10obj_order.csv')
