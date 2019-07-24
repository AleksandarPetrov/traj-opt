import pykep
import numpy as np

def process_single_pair(id_start, id_end, departure_dates, transfer_durations, dt):

    obj_start = pykep.planet.gtoc2(id_start)
    obj_end = pykep.planet.gtoc2(id_end)

    DV_matrix = np.zeros((len(transfer_durations), len(departure_dates)))

    for j, dep_date in enumerate(departure_dates):
        for i, transf_dur in enumerate(transfer_durations):

            # Handle times
            t_dep = pykep.epoch(dep_date)
            t_arr = pykep.epoch(dep_date+transf_dur)
            t_flight = (t_arr.mjd2000 - t_dep.mjd2000) * pykep.DAY2SEC

            # Calculate ephemerides
            r_start, v_start = obj_start.eph(t_dep)
            r_end, v_end = obj_end.eph(t_arr)

            # Solve the Lambert problem
            lambert_solution = pykep.lambert_problem(r_start, r_end, t_flight, pykep.MU_SUN, 5)

            # Compute the DV
            DV_start = np.min(np.linalg.norm(np.array(lambert_solution.get_v1()) - np.array(v_start)[np.newaxis, :], axis=1))
            DV_end = np.min(np.linalg.norm(np.array(lambert_solution.get_v2()) - np.array(v_end)[np.newaxis, :], axis=1))
            DV_total = DV_start + DV_end

            if np.isnan(DV_total):
                DV_total = np.inf
            DV_matrix[i,j] = DV_total

    return DV_matrix

if __name__ == '__main__':
    from plot_matrix import plot_matrix
    import time

    dt = 10 # descretization step, in days

    range_departure_date = (dt, 10000) # in MJD2000
    range_transfer_duration = (dt, 1000 ) # in days

    departure_dates = np.arange(start=range_departure_date[0], stop=range_departure_date[1]+1e-5, step=dt)
    transfer_durations = np.arange(start=range_transfer_duration[0], stop=range_transfer_duration[1]+1e-5, step=dt)

    t = time.time()
    DV_matrix = process_single_pair(id_start=111, id_end=121,
                                    departure_dates=departure_dates,
                                    transfer_durations=transfer_durations,
                                    dt=dt)
    print("Processing time: %.02f sec" % (time.time()-t))
    plot_matrix(DV_matrix, departure_dates, transfer_durations, output_name="both_111_121_10.png")
