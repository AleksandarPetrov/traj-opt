import numpy as np
import matplotlib.pyplot as plt

def plot_matrix(DV_matrix, departure_dates, transfer_durations, output_name='DV_matrix.png', threshold = 40):
    vplotmax = np.percentile(DV_matrix.flatten(), threshold)
    vplotmin = np.min(DV_matrix.flatten())

    fig = plt.figure()
    plt.imshow(DV_matrix, interpolation='nearest', origin='lower', vmin=vplotmin, vmax=vplotmax)
    plt.colorbar(orientation='horizontal')
    idxs_x = np.floor(np.linspace(0, len(departure_dates)-1, 5)).astype(int)
    idxs_y = np.floor(np.linspace(0, len(transfer_durations)-1, 5)).astype(int)
    plt.xticks(idxs_x, departure_dates[idxs_x])
    plt.yticks(idxs_y, transfer_durations[idxs_y])
    plt.savefig(output_name, dpi=300)

if __name__=='__main__':

    output_prefix = 'results_20obj/'
    filename='108_115_098_102_097_dt10'

    dt = 10 # descretization step, in days

    range_departure_date = (dt, 10000) # in MJD2000
    range_transfer_duration = (dt, 1000 ) # in days

    departure_dates = np.arange(start=range_departure_date[0], stop=range_departure_date[1]+1e-5, step=dt)
    transfer_durations = np.arange(start=range_transfer_duration[0], stop=range_transfer_duration[1]+1e-5, step=dt)
    DV_matrix = np.load(output_prefix+filename+'.npy')
    plot_matrix(DV_matrix, departure_dates, transfer_durations, output_name="DV_matrix_%s"%filename+".png")
